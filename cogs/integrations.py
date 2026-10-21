"""YouTube, Twitch and VK publication/live notifications per Discord server."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import disnake
import requests
from disnake.ext import commands, tasks

from database import get_guild_setting, set_guild_setting
from utils.colors import main_color

logger = logging.getLogger(__name__)
YT_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
HTTP_TIMEOUT = 12


def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
    response = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _get_text(url: str) -> str:
    response = requests.get(url, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.text


def _parse_list(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


class Integrations(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self._busy = False

    async def cog_load(self):
        self.poll_updates.start()

    def cog_unload(self):
        self.poll_updates.cancel()

    async def _get_list(self, guild_id: int, key: str) -> list[str]:
        raw = await get_guild_setting(guild_id, key, "")
        return _parse_list(raw)

    async def _set_list(self, guild_id: int, key: str, values: list[str]):
        await set_guild_setting(guild_id, key, ",".join(dict.fromkeys(values)))

    async def _send_update(self, guild: disnake.Guild, platform: str, title: str, url: str, details: str = ""):
        channel_id = await get_guild_setting(guild.id, "integration_channel_id")
        if not channel_id or not channel_id.isdigit():
            return
        channel = guild.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                logger.warning("Интеграции: канал %s недоступен на сервере %s", channel_id, guild.id)
                return
        if not hasattr(channel, "send"):
            return
        embed = disnake.Embed(title=title[:256], description=details[:3500] or None, url=url, color=main_color())
        embed.set_author(name=platform)
        embed.set_footer(text="Уведомление от Пушистика")
        await channel.send(embed=embed, allowed_mentions=disnake.AllowedMentions.none())

    async def _youtube(self, guild: disnake.Guild):
        channel_ids = await self._get_list(guild.id, "integration_youtube_ids")
        for channel_id in channel_ids[:10]:
            if not channel_id.startswith("UC") or len(channel_id) < 10:
                continue
            feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + urllib.parse.quote(channel_id)
            try:
                xml = await asyncio.to_thread(_get_text, feed_url)
                root = ET.fromstring(xml)
                entries = root.findall("atom:entry", YT_NS)
                if not entries:
                    continue
                videos = []
                for entry in entries:
                    video_id = entry.findtext("yt:videoId", default="", namespaces=YT_NS)
                    title = entry.findtext("atom:title", default="Новое видео", namespaces=YT_NS)
                    link = entry.find("atom:link", YT_NS)
                    href = link.attrib.get("href", "") if link is not None else ""
                    if video_id and href:
                        videos.append((video_id, title, href))
                if not videos:
                    continue
                seen_key = "integration_seen_youtube_" + channel_id
                last_seen = await get_guild_setting(guild.id, seen_key)
                latest_id = videos[0][0]
                if last_seen is None:
                    await set_guild_setting(guild.id, seen_key, latest_id)
                    continue
                new_videos = []
                for video_id, title, url in videos:
                    if video_id == last_seen:
                        break
                    new_videos.append((video_id, title, url))
                for video_id, title, url in reversed(new_videos):
                    await self._send_update(guild, "YouTube", "📺 Новое видео: " + title, url)
                if new_videos:
                    await set_guild_setting(guild.id, seen_key, latest_id)
            except Exception:
                logger.exception("Ошибка проверки YouTube-канала %s", channel_id)

    async def _twitch(self, guild: disnake.Guild):
        logins = await self._get_list(guild.id, "integration_twitch_logins")
        client_id = os.getenv("TWITCH_CLIENT_ID", "").strip()
        token = os.getenv("TWITCH_APP_TOKEN", "").strip()
        if not client_id or not token:
            return
        for login in logins[:10]:
            try:
                payload = await asyncio.to_thread(
                    _get_json,
                    "https://api.twitch.tv/helix/streams",
                    params={"user_login": login},
                    headers={"Client-Id": client_id, "Authorization": "Bearer " + token},
                )
                stream = next(iter(payload.get("data", [])), None)
                key = "integration_seen_twitch_" + login.lower()
                current_id = str(stream.get("id")) if stream else "offline"
                previous_id = await get_guild_setting(guild.id, key)
                if previous_id is None:
                    await set_guild_setting(guild.id, key, current_id)
                    continue
                if stream and current_id != previous_id:
                    title = stream.get("title") or "Начался эфир"
                    game = stream.get("game_name") or "Категория не указана"
                    url = "https://www.twitch.tv/" + login
                    await self._send_update(guild, "Twitch", "🔴 " + stream.get("user_name", login) + " начал(а) эфир", url, title + "\nКатегория: " + game)
                await set_guild_setting(guild.id, key, current_id)
            except Exception:
                logger.exception("Ошибка проверки Twitch-канала %s", login)

    async def _vk(self, guild: disnake.Guild):
        groups = await self._get_list(guild.id, "integration_vk_groups")
        token = os.getenv("VK_ACCESS_TOKEN", "").strip()
        if not token:
            return
        for group_id in groups[:10]:
            if not group_id.isdigit():
                continue
            try:
                payload = await asyncio.to_thread(
                    _get_json,
                    "https://api.vk.com/method/wall.get",
                    params={"owner_id": "-" + group_id, "count": 5, "access_token": token, "v": "5.199"},
                )
                if payload.get("error"):
                    logger.warning("VK API error for group %s: %s", group_id, payload["error"].get("error_msg"))
                    continue
                items = payload.get("response", {}).get("items", [])
                if not items:
                    continue
                latest_id = str(items[0].get("id", ""))
                key = "integration_seen_vk_" + group_id
                previous_id = await get_guild_setting(guild.id, key)
                if previous_id is None:
                    await set_guild_setting(guild.id, key, latest_id)
                    continue
                new_items = []
                for item in items:
                    item_id = str(item.get("id", ""))
                    if item_id == previous_id:
                        break
                    if item_id:
                        new_items.append(item)
                for item in reversed(new_items):
                    post_id = item.get("id")
                    text = (item.get("text") or "Новая публикация")[:500]
                    url = "https://vk.com/wall-" + group_id + "_" + str(post_id)
                    await self._send_update(guild, "VK", "💙 Новая публикация сообщества", url, text)
                if new_items:
                    await set_guild_setting(guild.id, key, latest_id)
            except Exception:
                logger.exception("Ошибка проверки VK-сообщества %s", group_id)

    @tasks.loop(minutes=5)
    async def poll_updates(self):
        if self._busy:
            return
        self._busy = True
        try:
            for guild in list(self.bot.guilds):
                await self._youtube(guild)
                await self._twitch(guild)
                await self._vk(guild)
        finally:
            self._busy = False

    @poll_updates.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()

    @commands.slash_command(name="интеграции", description="🔔 Настройка уведомлений YouTube, Twitch и VK")
    async def integrations(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @integrations.sub_command(name="канал", description="Выбрать канал для уведомлений интеграций")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_channel(self, inter: disnake.ApplicationCommandInteraction, канал: disnake.TextChannel):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        await set_guild_setting(inter.guild.id, "integration_channel_id", str(канал.id))
        await inter.response.send_message("✅ Уведомления интеграций будут публиковаться в " + канал.mention, ephemeral=True)

    @integrations.sub_command(name="youtube", description="Добавить YouTube channel ID для отслеживания")
    @commands.has_guild_permissions(manage_guild=True)
    async def add_youtube(self, inter: disnake.ApplicationCommandInteraction, channel_id: str = commands.Param(max_length=64)):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        channel_id = channel_id.strip()
        if not channel_id.startswith("UC") or len(channel_id) < 10 or any(ch.isspace() for ch in channel_id):
            await inter.response.send_message("❌ Укажи корректный YouTube channel ID, начинающийся с UC.", ephemeral=True)
            return
        values = await self._get_list(inter.guild.id, "integration_youtube_ids")
        if channel_id not in values:
            values.append(channel_id)
        await self._set_list(inter.guild.id, "integration_youtube_ids", values)
        await inter.response.send_message("✅ YouTube-канал добавлен. Новые публикации будут проверяться каждые 5 минут.", ephemeral=True)

    @integrations.sub_command(name="twitch", description="Добавить Twitch-логин для отслеживания")
    @commands.has_guild_permissions(manage_guild=True)
    async def add_twitch(self, inter: disnake.ApplicationCommandInteraction, логин: str = commands.Param(max_length=40)):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        login = логин.strip().lower()
        if not login.replace("_", "").isalnum():
            await inter.response.send_message("❌ Укажи корректный Twitch-логин.", ephemeral=True)
            return
        values = await self._get_list(inter.guild.id, "integration_twitch_logins")
        if login not in values:
            values.append(login)
        await self._set_list(inter.guild.id, "integration_twitch_logins", values)
        await inter.response.send_message("✅ Twitch-канал добавлен. Для работы нужны TWITCH_CLIENT_ID и TWITCH_APP_TOKEN в окружении хостинга.", ephemeral=True)

    @integrations.sub_command(name="vk", description="Добавить ID сообщества VK")
    @commands.has_guild_permissions(manage_guild=True)
    async def add_vk(self, inter: disnake.ApplicationCommandInteraction, id_сообщества: str = commands.Param(max_length=32)):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        group_id = id_сообщества.strip()
        if not group_id.isdigit():
            await inter.response.send_message("❌ Укажи числовой ID сообщества VK без знака минус.", ephemeral=True)
            return
        values = await self._get_list(inter.guild.id, "integration_vk_groups")
        if group_id not in values:
            values.append(group_id)
        await self._set_list(inter.guild.id, "integration_vk_groups", values)
        await inter.response.send_message("✅ Сообщество VK добавлено. Для работы нужен VK_ACCESS_TOKEN в окружении хостинга.", ephemeral=True)

    @integrations.sub_command(name="список", description="Показать настройки интеграций сервера")
    @commands.has_guild_permissions(manage_guild=True)
    async def list_integrations(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        channel_id = await get_guild_setting(inter.guild.id, "integration_channel_id")
        youtube = await self._get_list(inter.guild.id, "integration_youtube_ids")
        twitch = await self._get_list(inter.guild.id, "integration_twitch_logins")
        vk = await self._get_list(inter.guild.id, "integration_vk_groups")
        embed = disnake.Embed(title="🔔 Интеграции", color=main_color())
        embed.add_field(name="Канал уведомлений", value=f"<#{channel_id}>" if channel_id else "Не настроен", inline=False)
        embed.add_field(name="YouTube", value=", ".join(youtube) or "Нет каналов", inline=False)
        embed.add_field(name="Twitch", value=", ".join(twitch) or "Нет каналов", inline=False)
        embed.add_field(name="VK", value=", ".join(vk) or "Нет сообществ", inline=False)
        embed.set_footer(text="Проверка выполняется раз в 5 минут")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @integrations.sub_command(name="проверить", description="Проверить интеграции сейчас")
    @commands.has_guild_permissions(manage_guild=True)
    async def check_now(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        await inter.response.defer(ephemeral=True)
        await self._youtube(inter.guild)
        await self._twitch(inter.guild)
        await self._vk(inter.guild)
        await inter.followup.send("✅ Проверка завершена. Если найдено новое событие, уведомление отправлено в настроенный канал.", ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(Integrations(bot))
