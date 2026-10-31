"""Temporary voice rooms with a persistent button-based control panel."""

import logging
import os
import re

import aiosqlite
import disnake
from disnake.ext import commands

from database import DB_PATH

logger = logging.getLogger(__name__)

PANEL_MARKER = "fluffy:temporary-voice-control-panel:v1"


def _read_id(name: str) -> int:
    try:
        return int(os.getenv(name, "0") or 0)
    except ValueError:
        logger.warning("Некорректный ID в переменной %s; временные комнаты отключены.", name)
        return 0


def parse_member_id(value: str) -> int | None:
    """Accept a Discord snowflake or a user mention."""
    match = re.fullmatch(r"\s*(?:<@!?(\d+)>|(\d+))\s*", value or "")
    if not match:
        return None
    return int(match.group(1) or match.group(2))


def normalize_room_name(value: str) -> str:
    name = " ".join((value or "").split()).strip()
    return name[:100]


def parse_user_limit(value: str) -> int | None:
    try:
        limit = int(value.strip())
    except (AttributeError, TypeError, ValueError):
        return None
    return limit if 0 <= limit <= 99 else None


class VoiceRoomModal(disnake.ui.Modal):
    def __init__(self, cog: "TemporaryVoiceRooms", action: str):
        self.cog = cog
        self.action = action
        labels = {
            "limit": ("Лимит участников", "0 — без ограничений", "0–99"),
            "rename": ("Новое название", "Например: уютное логово", "100 символов"),
            "grant": ("ID или упоминание участника", "@участник или ID", "ID участника"),
            "revoke": ("ID или упоминание участника", "@участник или ID", "ID участника"),
            "transfer": ("ID или упоминание нового владельца", "Новый владелец должен быть в комнате", "ID участника"),
        }
        label, placeholder, custom_id = labels[action]
        super().__init__(
            title={
                "limit": "Изменить лимит комнаты",
                "rename": "Переименовать комнату",
                "grant": "Выдать доступ",
                "revoke": "Забрать доступ",
                "transfer": "Передать владение",
            }[action],
            custom_id=f"fluffy:tempvoice:modal:{action}",
            components=[
                disnake.ui.TextInput(
                    label=label,
                    placeholder=placeholder,
                    custom_id="value",
                    required=True,
                    max_length=100,
                )
            ],
        )

    async def callback(self, interaction: disnake.ModalInteraction):
        value = interaction.text_values.get("value", "")
        await self.cog.apply_modal_action(interaction, self.action, value)


class TemporaryVoicePanel(disnake.ui.View):
    def __init__(self, cog: "TemporaryVoiceRooms"):
        super().__init__(timeout=None)
        self.cog = cog

    @disnake.ui.button(label="🔒 Закрыть / открыть", style=disnake.ButtonStyle.secondary, custom_id="fluffy:tempvoice:toggle", row=0)
    async def toggle_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        room = await self.cog.get_controlled_room(inter)
        if room is None:
            return
        overwrite = room.overwrites_for(inter.guild.default_role)
        is_closed = overwrite.connect is False
        try:
            await room.set_permissions(
                inter.guild.default_role,
                connect=None if is_closed else False,
                reason=f"Изменение доступа к комнате владельцем {inter.author.id}",
            )
        except disnake.HTTPException:
            await inter.response.send_message("❌ Не удалось изменить доступ к комнате. Проверь права Fluffy.", ephemeral=True)
            return
        state = "открыта" if is_closed else "закрыта"
        await inter.response.send_message(f"✅ Комната теперь {state}.", ephemeral=True)

    @disnake.ui.button(label="👥 Лимит", style=disnake.ButtonStyle.secondary, custom_id="fluffy:tempvoice:limit", row=0)
    async def limit_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await self.cog.get_controlled_room(inter) is not None:
            await inter.response.send_modal(VoiceRoomModal(self.cog, "limit"))

    @disnake.ui.button(label="✏️ Название", style=disnake.ButtonStyle.secondary, custom_id="fluffy:tempvoice:rename", row=0)
    async def rename_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await self.cog.get_controlled_room(inter) is not None:
            await inter.response.send_modal(VoiceRoomModal(self.cog, "rename"))

    @disnake.ui.button(label="➕ Выдать доступ", style=disnake.ButtonStyle.success, custom_id="fluffy:tempvoice:grant", row=1)
    async def grant_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await self.cog.get_controlled_room(inter) is not None:
            await inter.response.send_modal(VoiceRoomModal(self.cog, "grant"))

    @disnake.ui.button(label="➖ Забрать доступ", style=disnake.ButtonStyle.danger, custom_id="fluffy:tempvoice:revoke", row=1)
    async def revoke_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await self.cog.get_controlled_room(inter) is not None:
            await inter.response.send_modal(VoiceRoomModal(self.cog, "revoke"))

    @disnake.ui.button(label="👑 Передать владельца", style=disnake.ButtonStyle.primary, custom_id="fluffy:tempvoice:transfer", row=1)
    async def transfer_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await self.cog.get_controlled_room(inter) is not None:
            await inter.response.send_modal(VoiceRoomModal(self.cog, "transfer"))

    @disnake.ui.button(label="🗑️ Удалить комнату", style=disnake.ButtonStyle.danger, custom_id="fluffy:tempvoice:delete", row=2)
    async def delete_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        room = await self.cog.get_controlled_room(inter)
        if room is None:
            return
        try:
            await room.delete(reason=f"Владелец {inter.author.id} удалил временную комнату")
        except disnake.HTTPException:
            await inter.response.send_message("❌ Не удалось удалить комнату. Проверь права Fluffy.", ephemeral=True)
            return
        await self.cog.remove_room(room.id)
        await inter.response.send_message("✅ Комната удалена.", ephemeral=True)


class TemporaryVoiceRooms(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.lobby_id = _read_id("TEMP_VOICE_LOBBY_ID")
        self.category_id = _read_id("TEMP_VOICE_CATEGORY_ID")
        self.control_channel_id = _read_id("TEMP_VOICE_CONTROL_CHANNEL_ID")
        self.prefix = os.getenv("TEMP_VOICE_PREFIX", "🔊・").strip() or "🔊・"
        self.panel_view = TemporaryVoicePanel(self)

    async def cog_load(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS temporary_voice_rooms (
                    channel_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    owner_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()
        self.bot.add_view(self.panel_view)

    async def get_controlled_room(self, inter: disnake.MessageInteraction | disnake.ModalInteraction):
        member = inter.author
        if not member.voice or not member.voice.channel:
            await inter.response.send_message("❌ Сначала зайди в свою временную голосовую комнату.", ephemeral=True)
            return None

        room = member.voice.channel
        if not isinstance(room, disnake.VoiceChannel):
            await inter.response.send_message("❌ Не удалось определить голосовую комнату.", ephemeral=True)
            return None

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT owner_id FROM temporary_voice_rooms WHERE channel_id = ? AND guild_id = ?",
                (room.id, inter.guild.id),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            await inter.response.send_message("❌ Эта комната не управляется Fluffy.", ephemeral=True)
            return None

        is_owner = row[0] == member.id
        is_admin = member.guild_permissions.administrator
        if not is_owner and not is_admin:
            await inter.response.send_message("❌ Управлять комнатой может только её владелец или администратор.", ephemeral=True)
            return None
        return room

    async def remove_room(self, channel_id: int):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM temporary_voice_rooms WHERE channel_id = ?", (channel_id,))
            await db.commit()

    async def apply_modal_action(self, inter: disnake.ModalInteraction, action: str, value: str):
        room = await self.get_controlled_room(inter)
        if room is None:
            return

        if action == "limit":
            limit = parse_user_limit(value)
            if limit is None:
                await inter.response.send_message("❌ Укажи целое число от 0 до 99. Значение 0 снимает лимит.", ephemeral=True)
                return
            try:
                await room.edit(user_limit=limit, reason=f"Лимит изменён владельцем {inter.author.id}")
            except disnake.HTTPException:
                await inter.response.send_message("❌ Не удалось изменить лимит. Проверь права Fluffy.", ephemeral=True)
                return
            await inter.response.send_message("✅ Лимит снят." if limit == 0 else f"✅ Лимит установлен: {limit}.", ephemeral=True)
            return

        if action == "rename":
            name = normalize_room_name(value)
            if not name:
                await inter.response.send_message("❌ Название не может быть пустым.", ephemeral=True)
                return
            try:
                await room.edit(name=name, reason=f"Название изменено владельцем {inter.author.id}")
            except disnake.HTTPException:
                await inter.response.send_message("❌ Не удалось переименовать комнату.", ephemeral=True)
                return
            await inter.response.send_message(f"✅ Новое название: **{name}**", ephemeral=True)
            return

        target_id = parse_member_id(value)
        if target_id is None:
            await inter.response.send_message("❌ Не удалось распознать участника. Укажи его упоминание или числовой ID.", ephemeral=True)
            return
        target = inter.guild.get_member(target_id)
        if target is None:
            try:
                target = await inter.guild.fetch_member(target_id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                target = None
        if target is None or target.bot:
            await inter.response.send_message("❌ Участник не найден на сервере или это бот.", ephemeral=True)
            return
        if target.id == inter.author.id:
            await inter.response.send_message("❌ Нельзя выбрать самого себя.", ephemeral=True)
            return

        if action == "grant":
            try:
                await room.set_permissions(target, view_channel=True, connect=True, reason=f"Доступ выдан владельцем {inter.author.id}")
            except disnake.HTTPException:
                await inter.response.send_message("❌ Не удалось выдать доступ. Проверь права Fluffy.", ephemeral=True)
                return
            await inter.response.send_message(f"✅ {target.mention} теперь может видеть комнату и подключаться к ней.", ephemeral=True)
            return

        if action == "revoke":
            try:
                await room.set_permissions(target, view_channel=False, connect=False, reason=f"Доступ отозван владельцем {inter.author.id}")
            except disnake.HTTPException:
                await inter.response.send_message("❌ Не удалось забрать доступ. Проверь права Fluffy.", ephemeral=True)
                return
            await inter.response.send_message(f"✅ Доступ для {target.mention} закрыт.", ephemeral=True)
            return

        if action == "transfer":
            if not target.voice or not target.voice.channel or target.voice.channel.id != room.id:
                await inter.response.send_message("❌ Новый владелец должен находиться в этой голосовой комнате.", ephemeral=True)
                return
            async with aiosqlite.connect(str(DB_PATH)) as db:
                await db.execute(
                    "UPDATE temporary_voice_rooms SET owner_id = ? WHERE channel_id = ? AND guild_id = ?",
                    (target.id, room.id, inter.guild.id),
                )
                await db.commit()
            await inter.response.send_message(f"👑 Владение комнатой передано {target.mention}.", ephemeral=True)

    async def ensure_panel(self):
        if not self.control_channel_id:
            return
        channel = self.bot.get_channel(self.control_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.control_channel_id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                logger.warning("Не удалось получить канал панели временных войсов: %s", self.control_channel_id)
                return
        if not isinstance(channel, disnake.TextChannel):
            logger.warning("TEMP_VOICE_CONTROL_CHANNEL_ID должен указывать на текстовый канал.")
            return

        embed = disnake.Embed(
            title="🎛️ Управление приватной комнатой",
            description=(
                "Зайди в свою временную голосовую комнату и выбери действие ниже.\n\n"
                "🔒 Закрыть или открыть комнату\n"
                "👥 Установить лимит участников\n"
                "✏️ Изменить название\n"
                "➕ Выдать или ➖ забрать доступ\n"
                "👑 Передать владение участнику в комнате\n"
                "🗑️ Удалить свою комнату\n\n"
                "Кнопки доступны владельцу комнаты и администраторам."
            ),
            color=disnake.Color.from_rgb(119, 139, 214),
        )
        embed.set_footer(text=PANEL_MARKER)

        try:
            async for message in channel.history(limit=100):
                if message.author.id != self.bot.user.id or not message.embeds:
                    continue
                footer = message.embeds[0].footer.text if message.embeds[0].footer else ""
                if footer == PANEL_MARKER:
                    await message.edit(embed=embed, view=self.panel_view)
                    return
            await channel.send(embed=embed, view=self.panel_view)
        except disnake.Forbidden:
            logger.warning("Нет прав на чтение истории/отправку панели в канале %s.", channel.id)
        except disnake.HTTPException:
            logger.exception("Не удалось обновить панель временных войсов.")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_panel()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        if member.bot or member.guild is None:
            return

        if after.channel and after.channel.id == self.lobby_id and before.channel != after.channel:
            lobby = after.channel
            async with aiosqlite.connect(str(DB_PATH)) as db:
                async with db.execute(
                    "SELECT channel_id FROM temporary_voice_rooms WHERE guild_id = ? AND owner_id = ?",
                    (member.guild.id, member.id),
                ) as cursor:
                    existing = await cursor.fetchone()
            if existing:
                existing_room = member.guild.get_channel(existing[0])
                if isinstance(existing_room, disnake.VoiceChannel):
                    try:
                        await member.move_to(existing_room, reason="Возврат в свою временную комнату")
                    except disnake.HTTPException:
                        logger.exception("Не удалось вернуть участника %s в его комнату.", member.id)
                    return
                await self.remove_room(existing[0])

            category = member.guild.get_channel(self.category_id) if self.category_id else lobby.category
            try:
                room = await member.guild.create_voice_channel(
                    name=f"{self.prefix}{member.display_name}"[:100],
                    category=category,
                    overwrites=lobby.overwrites,
                    reason=f"Temporary voice room for {member} ({member.id})",
                )
                await room.set_permissions(member, view_channel=True, connect=True)
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO temporary_voice_rooms (channel_id, guild_id, owner_id) VALUES (?, ?, ?)",
                        (room.id, member.guild.id, member.id),
                    )
                    await db.commit()
                await member.move_to(room, reason="Перемещение в личную временную комнату")
            except (disnake.Forbidden, disnake.HTTPException):
                logger.exception("Не удалось создать временную комнату для участника %s", member.id)
                if "room" in locals():
                    await self.remove_room(room.id)
                    try:
                        await room.delete(reason="Не удалось переместить владельца во временную комнату")
                    except disnake.HTTPException:
                        logger.exception("Не удалось удалить незавершённую комнату %s", room.id)
                return

        old_channel = before.channel
        if not old_channel or old_channel.id == self.lobby_id or not isinstance(old_channel, disnake.VoiceChannel):
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT owner_id FROM temporary_voice_rooms WHERE channel_id = ? AND guild_id = ?",
                (old_channel.id, member.guild.id),
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return

            if not old_channel.members:
                await db.execute("DELETE FROM temporary_voice_rooms WHERE channel_id = ?", (old_channel.id,))
                await db.commit()
                try:
                    await old_channel.delete(reason="Пустая временная голосовая комната")
                except (disnake.Forbidden, disnake.HTTPException):
                    logger.exception("Не удалось удалить пустую комнату %s", old_channel.id)
                return

            if row[0] == member.id:
                next_owner = next((m for m in old_channel.members if not m.bot), None)
                if next_owner:
                    await db.execute(
                        "UPDATE temporary_voice_rooms SET owner_id = ? WHERE channel_id = ?",
                        (next_owner.id, old_channel.id),
                    )
                    await db.commit()
                    logger.info("Владение комнатой %s передано участнику %s.", old_channel.id, next_owner.id)


def setup(bot: commands.InteractionBot):
    bot.add_cog(TemporaryVoiceRooms(bot))
