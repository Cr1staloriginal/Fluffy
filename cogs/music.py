"""YouTube audio player for Discord voice channels (requires FFmpeg and PyNaCl)."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

import disnake
from disnake.ext import commands

try:
    import yt_dlp
except ImportError:  # Keep the rest of the bot usable if the optional dependency is absent.
    yt_dlp = None

logger = logging.getLogger(__name__)
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
}


@dataclass
class Track:
    title: str
    webpage_url: str
    requested_by: int


class Music(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.queues: dict[int, deque[Track]] = defaultdict(deque)
        self.current: dict[int, Track] = {}
        self.repeat: dict[int, bool] = defaultdict(bool)
        self.stopping: set[int] = set()
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def _extract_track(self, query: str, requester_id: int) -> Track:
        if yt_dlp is None:
            raise RuntimeError("Не установлен yt-dlp. Добавь зависимость из requirements.txt и перезапусти бота.")
        target = query.strip()
        if not target:
            raise ValueError("Укажи ссылку на YouTube или поисковый запрос.")
        if not target.startswith(("https://", "http://")):
            target = "ytsearch1:" + target

        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(target, download=False)
                if info.get("entries"):
                    info = next((entry for entry in info["entries"] if entry), None)
                if not info:
                    raise ValueError("Ничего не найдено.")
                return info.get("title") or "Без названия", info.get("webpage_url") or info.get("original_url") or target

        title, url = await asyncio.to_thread(extract)
        return Track(title=title, webpage_url=url, requested_by=requester_id)

    async def _resolve_stream(self, url: str) -> str:
        if yt_dlp is None:
            raise RuntimeError("Не установлен yt-dlp.")

        def extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get("entries"):
                    info = next((entry for entry in info["entries"] if entry), None)
                if not info or not info.get("url"):
                    raise ValueError("Не удалось получить аудиопоток.")
                return info["url"]

        return await asyncio.to_thread(extract)

    async def _start_track(self, guild: disnake.Guild):
        guild_id = guild.id
        async with self._locks[guild_id]:
            voice = guild.voice_client
            if voice is None or not voice.is_connected():
                self.current.pop(guild_id, None)
                return
            if voice.is_playing() or voice.is_paused():
                return
            if not self.queues[guild_id]:
                self.current.pop(guild_id, None)
                return

            track = self.queues[guild_id].popleft()
            self.current[guild_id] = track
            try:
                stream_url = await self._resolve_stream(track.webpage_url)
                source = disnake.FFmpegPCMAudio(
                    stream_url,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    options="-vn",
                )
                voice.play(
                    source,
                    after=lambda error: asyncio.run_coroutine_threadsafe(
                        self._after_track(guild_id, error), self.bot.loop
                    ),
                )
                logger.info("Музыка: воспроизведение %s на сервере %s", track.title, guild_id)
            except Exception:
                logger.exception("Не удалось воспроизвести трек на сервере %s", guild_id)
                self.current.pop(guild_id, None)
                if self.queues[guild_id]:
                    asyncio.create_task(self._start_track(guild))

    async def _after_track(self, guild_id: int, error: Optional[Exception]):
        if error:
            logger.warning("Ошибка аудиоплеера на сервере %s: %s", guild_id, error)
        if guild_id in self.stopping:
            self.stopping.discard(guild_id)
            self.current.pop(guild_id, None)
            return
        current = self.current.get(guild_id)
        if current and self.repeat[guild_id]:
            self.queues[guild_id].appendleft(current)
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._start_track(guild)

    async def _ensure_voice(self, inter: disnake.ApplicationCommandInteraction) -> disnake.VoiceClient:
        if inter.guild is None:
            raise ValueError("Музыка доступна только на сервере.")
        member = inter.author
        if not isinstance(member, disnake.Member) or not member.voice or not member.voice.channel:
            raise ValueError("Сначала зайди в голосовой канал.")
        channel = member.voice.channel
        voice = inter.guild.voice_client
        if voice and voice.is_connected():
            if voice.channel != channel:
                raise ValueError("Я уже нахожусь в другом голосовом канале.")
            return voice
        return await channel.connect()

    async def _fail(self, inter: disnake.ApplicationCommandInteraction, message: str):
        if inter.response.is_done():
            await inter.followup.send("❌ " + message, ephemeral=True)
        else:
            await inter.response.send_message("❌ " + message, ephemeral=True)

    @commands.slash_command(name="музыка", description="🎵 Музыка в голосовом канале")
    async def music(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @music.sub_command(name="плей", description="Добавить трек из YouTube в очередь")
    async def play(self, inter: disnake.ApplicationCommandInteraction, запрос: str = commands.Param(max_length=500)):
        await inter.response.defer(ephemeral=True)
        try:
            voice = await self._ensure_voice(inter)
            track = await self._extract_track(запрос, inter.author.id)
            guild_id = inter.guild.id
            self.queues[guild_id].append(track)
            position = len(self.queues[guild_id])
            if not voice.is_playing() and not voice.is_paused():
                await self._start_track(inter.guild)
                message = "▶️ Добавлено в очередь: " + track.title
            else:
                message = f"🎶 Добавлено в очередь (позиция {position}): {track.title}"
            await inter.followup.send(message, ephemeral=True)
        except Exception as exc:
            await self._fail(inter, str(exc))

    @music.sub_command(name="пауза", description="Приостановить воспроизведение")
    async def pause(self, inter: disnake.ApplicationCommandInteraction):
        voice = inter.guild.voice_client if inter.guild else None
        if voice and voice.is_playing():
            voice.pause()
            await inter.response.send_message("⏸️ Воспроизведение приостановлено.", ephemeral=True)
        else:
            await inter.response.send_message("Сейчас нечего ставить на паузу.", ephemeral=True)

    @music.sub_command(name="возобновить", description="Продолжить воспроизведение")
    async def resume(self, inter: disnake.ApplicationCommandInteraction):
        voice = inter.guild.voice_client if inter.guild else None
        if voice and voice.is_paused():
            voice.resume()
            await inter.response.send_message("▶️ Воспроизведение продолжено.", ephemeral=True)
        else:
            await inter.response.send_message("Музыка не находится на паузе.", ephemeral=True)

    @music.sub_command(name="пропустить", description="Пропустить текущий трек")
    async def skip(self, inter: disnake.ApplicationCommandInteraction):
        voice = inter.guild.voice_client if inter.guild else None
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            await inter.response.send_message("⏭️ Трек пропущен.", ephemeral=True)
        else:
            await inter.response.send_message("Сейчас нечего пропускать.", ephemeral=True)

    @music.sub_command(name="стоп", description="Остановить музыку и очистить очередь")
    async def stop(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        guild_id = inter.guild.id
        self.queues[guild_id].clear()
        self.repeat[guild_id] = False
        voice = inter.guild.voice_client
        if voice:
            self.stopping.add(guild_id)
            if voice.is_playing() or voice.is_paused():
                voice.stop()
            await voice.disconnect(force=True)
        self.current.pop(guild_id, None)
        self.stopping.discard(guild_id)
        await inter.response.send_message("⏹️ Музыка остановлена, очередь очищена.", ephemeral=True)

    @music.sub_command(name="очередь", description="Показать текущий трек и очередь")
    async def queue(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        guild_id = inter.guild.id
        lines = []
        current = self.current.get(guild_id)
        if current:
            lines.append("▶️ Сейчас: " + current.title)
        tracks = list(self.queues[guild_id])
        lines.extend(f"{index}. {track.title}" for index, track in enumerate(tracks[:15], 1))
        if len(tracks) > 15:
            lines.append(f"… и ещё {len(tracks) - 15} треков")
        embed = disnake.Embed(title="🎵 Очередь Пушистика", description="\n".join(lines) or "Очередь пуста.", color=disnake.Color(0xB3D1F3))
        embed.set_footer(text="Повтор включён" if self.repeat[guild_id] else "Повтор выключен")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @music.sub_command(name="повтор", description="Включить или выключить повтор текущего трека")
    async def repeat_track(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        guild_id = inter.guild.id
        self.repeat[guild_id] = not self.repeat[guild_id]
        await inter.response.send_message(
            "🔁 Повтор включён." if self.repeat[guild_id] else "➡️ Повтор выключен.",
            ephemeral=True,
        )

    @music.sub_command(name="сейчас", description="Показать текущий трек")
    async def now_playing(self, inter: disnake.ApplicationCommandInteraction):
        track = self.current.get(inter.guild.id) if inter.guild else None
        if not track:
            await inter.response.send_message("Сейчас ничего не воспроизводится.", ephemeral=True)
            return
        embed = disnake.Embed(title="🎧 Сейчас играет", description=f"[{track.title}]({track.webpage_url})", color=disnake.Color(0xB3D1F3))
        await inter.response.send_message(embed=embed)

    def cog_unload(self):
        for guild in self.bot.guilds:
            voice = guild.voice_client
            if voice and voice.is_connected():
                voice.stop()
                asyncio.create_task(voice.disconnect(force=True))


def setup(bot: commands.InteractionBot):
    bot.add_cog(Music(bot))
