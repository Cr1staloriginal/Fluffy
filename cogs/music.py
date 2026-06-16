import disnake
from disnake.ext import commands
import yt_dlp
import asyncio
import os
from collections import deque
from utils.colors import main_color

# Настройки yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

class YTDLSource(disnake.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(disnake.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.queue = {}  # guild_id: deque of (url, title)
        self.current = {}  # guild_id: YTDLSource
        self.loop = {}  # guild_id: bool
        self.voice_clients = {}  # guild_id: voice client

    async def get_voice_client(self, guild_id):
        return self.voice_clients.get(guild_id)

    async def play_next(self, guild_id):
        if guild_id not in self.queue or not self.queue[guild_id]:
            self.current[guild_id] = None
            # Если режим повтора включён, не останавливаем
            if self.loop.get(guild_id, False) and self.current.get(guild_id):
                # Повтор текущего трека
                url = self.current[guild_id].url
                title = self.current[guild_id].title
                self.queue[guild_id].append((url, title))
            return
        url, title = self.queue[guild_id].popleft()
        source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        self.current[guild_id] = source
        vc = self.voice_clients.get(guild_id)
        if vc:
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop))

    async def send_now_playing(self, guild_id, channel):
        if guild_id not in self.current or not self.current[guild_id]:
            return
        source = self.current[guild_id]
        embed = disnake.Embed(title="🎵 Сейчас играет", description=f"**{source.title}**", color=main_color())
        if hasattr(source, 'url'):
            embed.add_field(name="Ссылка", value=source.url, inline=False)
        await channel.send(embed=embed)

    @commands.slash_command(name="плей", description="🎵 Воспроизвести музыку (по ссылке или поисковому запросу)")
    async def play(self, inter: disnake.ApplicationCommandInteraction, запрос: str):
        """Воспроизводит музыку в голосовом канале."""
        await inter.response.defer()
        member = inter.author
        voice_state = member.voice
        if not voice_state or not voice_state.channel:
            await inter.edit_original_response("❌ Вы должны быть в голосовом канале.")
            return
        guild_id = inter.guild.id
        vc = self.voice_clients.get(guild_id)
        if not vc:
            vc = await voice_state.channel.connect()
            self.voice_clients[guild_id] = vc
        if guild_id not in self.queue:
            self.queue[guild_id] = deque()
        if not запрос.startswith('http'):
            запрос = f"ytsearch:{запрос}"
        try:
            ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(запрос, download=False))
            if 'entries' in info:
                entry = info['entries'][0]
                url = entry['webpage_url']
                title = entry.get('title', 'Неизвестно')
            else:
                url = info['webpage_url']
                title = info.get('title', 'Неизвестно')
            self.queue[guild_id].append((url, title))
            await inter.edit_original_response(f"✅ Добавлено в очередь: **{title}**")
            if not self.current.get(guild_id):
                await self.play_next(guild_id)
                # Отправляем уведомление о текущем треке в канал
                await self.send_now_playing(guild_id, inter.channel)
        except Exception as e:
            await inter.edit_original_response(f"❌ Ошибка: {e}")

    @commands.slash_command(name="пауза", description="⏸️ Поставить воспроизведение на паузу")
    async def pause(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.pause()
            await inter.response.send_message("⏸️ Воспроизведение приостановлено.")
        else:
            await inter.response.send_message("❌ Сейчас ничего не играет.")

    @commands.slash_command(name="возобновить", description="▶️ Возобновить воспроизведение")
    async def resume(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_paused():
            vc.resume()
            await inter.response.send_message("▶️ Воспроизведение возобновлено.")
        else:
            await inter.response.send_message("❌ Музыка не на паузе.")

    @commands.slash_command(name="пропустить", description="⏭️ Пропустить текущий трек")
    async def skip(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.stop()
            await inter.response.send_message("⏭️ Трек пропущен.")
            await self.play_next(guild_id)
            if self.current.get(guild_id):
                await self.send_now_playing(guild_id, inter.channel)
        else:
            await inter.response.send_message("❌ Сейчас ничего не играет.")

    @commands.slash_command(name="стоп", description="⏹️ Остановить воспроизведение и очистить очередь")
    async def stop(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc:
            vc.stop()
            self.queue[guild_id] = deque()
            self.current[guild_id] = None
            await vc.disconnect()
            del self.voice_clients[guild_id]
            await inter.response.send_message("⏹️ Воспроизведение остановлено, бот покинул канал.")
        else:
            await inter.response.send_message("❌ Бот не в голосовом канале.")

    @commands.slash_command(name="очередь", description="📋 Показать очередь треков")
    async def show_queue(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        if guild_id not in self.queue or not self.queue[guild_id]:
            await inter.response.send_message("📭 Очередь пуста.")
            return
        q_list = [f"{i+1}. {title}" for i, (_, title) in enumerate(self.queue[guild_id])]
        q_text = "\n".join(q_list[:10])
        if len(q_list) > 10:
            q_text += f"\n... и ещё {len(q_list)-10} треков."
        embed = disnake.Embed(title="📋 Очередь", description=q_text, color=main_color())
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="повтор", description="🔁 Включить/выключить повтор текущего трека")
    async def loop(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        if guild_id not in self.loop:
            self.loop[guild_id] = False
        self.loop[guild_id] = not self.loop[guild_id]
        state = "включён" if self.loop[guild_id] else "выключен"
        await inter.response.send_message(f"🔁 Режим повтора {state}.")

    @commands.slash_command(name="сейчас", description="🎶 Показать текущий трек")
    async def nowplaying(self, inter: disnake.ApplicationCommandInteraction):
        guild_id = inter.guild.id
        if guild_id not in self.current or not self.current[guild_id]:
            await inter.response.send_message("❌ Сейчас ничего не играет.")
            return
        source = self.current[guild_id]
        embed = disnake.Embed(title="🎵 Сейчас играет", description=f"**{source.title}**", color=main_color())
        if hasattr(source, 'url'):
            embed.add_field(name="Ссылка", value=source.url, inline=False)
        await inter.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if member.id == self.bot.user.id:
            return
        guild = member.guild
        if guild.id in self.voice_clients:
            vc = self.voice_clients[guild.id]
            if vc and len(vc.channel.members) == 1:
                await asyncio.sleep(60)
                if len(vc.channel.members) == 1:
                    await vc.disconnect()
                    del self.voice_clients[guild.id]
                    self.current[guild.id] = None
                    self.queue[guild.id] = deque()

def setup(bot: commands.InteractionBot):
    bot.add_cog(Music(bot))