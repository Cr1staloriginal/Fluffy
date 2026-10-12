import disnake
from disnake.ext import commands, tasks
import datetime
import random
import os
import asyncio
from utils.seasons import get_current_season, get_season_name, get_local_time
from database import get_setting, set_setting


# ===== ЧАСОВОЙ ПОЯС =====
# По умолчанию — Москва (UTC+3). Можно изменить через переменную окружения TIMEZONE_OFFSET
try:
    TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", "3"))
    if not -12 <= TIMEZONE_OFFSET <= 14:
        raise ValueError
except (TypeError, ValueError):
    TIMEZONE_OFFSET = 3
SERVER_TZ = datetime.timezone(datetime.timedelta(hours=TIMEZONE_OFFSET))


class AutoMessages(commands.Cog):
    @staticmethod
    def _read_int(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(os.getenv(name, str(default)))
            return value if minimum <= value <= maximum else default
        except (TypeError, ValueError):
            return default

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.channel_id = self._read_int("AUTO_MESSAGE_CHANNEL_ID", 0, 0, 2**63 - 1)
        self.interval_minutes = self._read_int("AUTO_MESSAGE_INTERVAL", 60, 5, 1440)
        self.min_delay = self._read_int("AUTO_MESSAGE_MIN_DELAY", 0, 0, 1440)
        self.enabled = os.getenv("AUTO_MESSAGE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        self._last_send_error = None

        # Часы ночи (по локальному времени)
        self.night_start = self._read_int("NIGHT_START_HOUR", 23, 0, 23)
        self.night_end = self._read_int("NIGHT_END_HOUR", 6, 0, 23)

        # ===== ДНЕВНЫЕ СООБЩЕНИЯ =====
        self.messages_day = {
            "default": [
                "🐾 {bot} весело играет с хвостиком!",
                "☀️ {bot} наслаждается солнечным днём!",
                "🎉 {bot} раздаёт обнимашки всем вокруг!",
                "🍪 {bot} угощает всех печеньками!",
                "🎶 {bot} напевает весёлую песенку!",
                "🌟 {bot} сияет как звёздочка!",
                "🧸 {bot} обнимает плюшевого друга!",
                "🌸 {bot} расцвёл как весенний цветочек!",
                "🦊 {bot} резвится на поляне!",
                "🎈 {bot} дарит радость и лёгкость!",
                "✨ {bot} желает всем хорошего дня!",
                "🍃 {bot} гуляет по лесу и собирает цветочки!",
            ],
            "halloween": [
                "🎃 {bot} надел костюм призрака и пугает всех!",
                "👻 {bot} летает по серверу и шуршит!",
                "🦇 {bot} кружит над чатом в лунном свете!",
                "🕷️ {bot} плетёт паутину в уголке!",
                "🧛 {bot} ищет свежую кровь... то есть конфеты!",
                "🍬 {bot} требует сладости: «Сладость или гадость!»",
                "💀 {bot} восстал из мёртвых и вернулся в чат!",
                "🕯️ {bot} рассказывает страшные истории!",
                "🌕 {bot} воет на луну в эту жуткую ночь!",
                "⚰️ {bot} спрятался в гробу и ждёт Хэллоуина!",
            ],
            "new_year": [
                "🎄 {bot} наряжает ёлку к Новому году!",
                "🎁 {bot} ищет подарки под ёлкой!",
                "❄️ {bot} катается на санках с горки!",
                "⛄ {bot} лепит снеговика во дворе!",
                "🌟 {bot} загадывает желание под бой курантов!",
                "🍊 {bot} уплетает мандаринки!",
                "🔔 {bot} слушает звон колокольчиков!",
                "✨ {bot} запускает фейерверк в небо!",
                "🎅 {bot} ждёт Деда Мороза в гости!",
                "🎊 {bot} поздравляет всех с праздником!",
            ],
            "valentine": [
                "💖 {bot} дарит всем валентинки!",
                "🌹 {bot} вручает букет роз!",
                "💌 {bot} отправляет любовные письма!",
                "💕 {bot} признаётся в любви всему серверу!",
                "🧸 {bot} обнимает плюшевого мишку!",
                "🍫 {bot} угощает всех шоколадом!",
                "💘 {bot} попал в самое сердце!",
                "🥰 {bot} сияет от счастья и любви!",
                "💞 {bot} делится теплом с каждым!",
                "🎀 {bot} украшает всё сердечками!",
            ],
            "spring": [
                "🌸 {bot} встречает весну с букетом цветов!",
                "🌷 {bot} любуется первыми тюльпанами!",
                "🌼 {bot} собирает ромашки на поляне!",
                "☀️ {bot} греется под тёплым солнышком!",
                "🦋 {bot} гоняется за бабочками!",
                "🐝 {bot} слушает жужжание пчёл!",
                "🌱 {bot} сажает первые ростки!",
                "🍃 {bot} вдыхает свежий воздух!",
                "💐 {bot} поздравляет всех девочек с 8 марта!",
                "🌈 {bot} радуется весенней радуге!",
            ],
            "easter": [
                "🐣 {bot} нашёл пасхальное яйцо!",
                "🥚 {bot} красит яйца к Пасхе!",
                "🐰 {bot} встретил пасхального кролика!",
                "🍰 {bot} печёт кулич к празднику!",
                "🐇 {bot} ищет спрятанные яйца в саду!",
                "✨ {bot} радуется светлому празднику!",
                "🐥 {bot} играет с цыплятами!",
                "🎨 {bot} делает пасхальные поделки!",
                "🌞 {bot} радуется тёплому дню!",
                "🍬 {bot} делится пасхальными сладостями!",
            ],
            "server_birthday": [
                "🎂 {bot} празднует день рождения сервера!",
                "🎉 {bot} запускает салют в честь праздника!",
                "🎁 {bot} дарит подарки всем участникам!",
                "🥳 {bot} веселится на дне рождения!",
                "🎈 {bot} надувает шарики для праздника!",
                "🍰 {bot} угощает всех тортом!",
                "🎊 {bot} устраивает большой праздник!",
                "✨ {bot} загадывает желание для сервера!",
                "🌟 {bot} желает серверу процветания!",
                "💝 {bot} дарит частичку тепла в этот день!",
            ],
        }

        # ===== НОЧНЫЕ СООБЩЕНИЯ =====
        self.messages_night = [
            "🌙 {bot} сладко спит, завернувшись в клубочек...",
            "💤 {bot} видит пушистые сны...",
            "🛌 {bot} уютно устроился на облачке!",
            "🌜 {bot} желает всем спокойной ночи!",
            "✨ {bot} сторожит ваши сны!",
            "🧸 {bot} обнимает подушку и мурчит...",
            "🌙 {bot} свернулся калачиком и посапывает.",
            "💫 {bot} ловит звёздочки во сне!",
            "🌌 {bot} тихо посапывает под звёздным небом...",
            "😴 {bot} зевает и укладывается спать...",
            "🌛 {bot} видит сон о тёплых объятиях...",
            "⭐ {bot} спит под одеялом из звёздочек!",
        ]



    async def cog_load(self):
        # SQLite overrides environment defaults for settings changed through slash commands.
        saved_channel = await get_setting("auto_message_channel_id")
        saved_interval = await get_setting("auto_message_interval")
        if saved_channel is not None:
            self.channel_id = self._read_int_value(saved_channel, self.channel_id, 0, 2**63 - 1)
        if saved_interval is not None:
            self.interval_minutes = self._read_int_value(saved_interval, self.interval_minutes, 5, 1440)
        self.auto_message.change_interval(minutes=self.interval_minutes)
        if self.enabled:
            self.auto_message.start()
        else:
            print("[AutoMessages] Автосообщения отключены в настройках окружения")

    @staticmethod
    def _read_int_value(raw: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(raw)
            return value if minimum <= value <= maximum else default
        except (TypeError, ValueError):
            return default

    def cog_unload(self):
        if self.auto_message.is_running():
            self.auto_message.cancel()

    def is_night(self) -> bool:
        """Проверяет, ночь ли сейчас (по локальному времени)."""
        now = get_local_time()
        hour = now.hour
        if self.night_start > self.night_end:
            # Например, 23 → 6 (через полночь)
            return hour >= self.night_start or hour < self.night_end
        else:
            # Например, 0 → 6
            return self.night_start <= hour < self.night_end

    @tasks.loop(minutes=60)
    async def auto_message(self):
        if not self.channel_id:
            self._last_send_error = "AUTO_MESSAGE_CHANNEL_ID не настроен"
            return False
        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                self._last_send_error = f"Канал {self.channel_id} недоступен"
                return False
        if not hasattr(channel, "send"):
            self._last_send_error = "Указанный канал не поддерживает отправку сообщений"
            return False

        now = get_local_time()

        if self.is_night():
            msg = random.choice(self.messages_night)
        else:
            season = get_current_season()
            messages = self.messages_day.get(season, self.messages_day["default"])
            msg = random.choice(messages)

        text = msg.format(bot=self.bot.user.display_name)

        try:
            await channel.send(text)
            self._last_send_error = None
            print(f"[AutoMessages] ({now.strftime('%H:%M %d.%m')}) Отправлено: {text}")
            return True
        except (disnake.Forbidden, disnake.HTTPException) as e:
            self._last_send_error = str(e)
            print(f"[AutoMessages] Ошибка отправки: {e}")
            return False

    @auto_message.before_loop
    async def before_auto_message(self):
        await self.bot.wait_until_ready()
        if self.min_delay > 0:
            delay = random.randint(0, self.min_delay * 60)
            print(f"[AutoMessages] Первое сообщение через {delay // 60} мин {delay % 60} сек")
            await asyncio.sleep(delay)
        now = get_local_time()
        print(f"[AutoMessages] Запущено. Локальное время бота: {now.strftime('%H:%M %d.%m.%Y %Z')}")

    # ===== КОМАНДЫ =====
    @commands.slash_command(name="автосообщение", description="⚙️ Управление автосообщениями")
    @commands.has_permissions(administrator=True)
    async def auto_group(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @auto_group.sub_command(name="статус", description="Показать статус автосообщений")
    async def status(self, inter: disnake.ApplicationCommandInteraction):
        channel = self.bot.get_channel(self.channel_id)
        channel_text = channel.mention if channel else "❌ не найден"
        season = get_current_season()
        running = "✅ Включены" if self.auto_message.is_running() else "❌ Выключены"

        now_local = get_local_time()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        night_status = "🌙 Ночь" if self.is_night() else "☀️ День"

        embed = disnake.Embed(title="📢 Автосообщения", color=disnake.Color.blurple())
        embed.add_field(name="Статус", value=running, inline=True)
        embed.add_field(name="Канал", value=channel_text, inline=True)
        embed.add_field(name="Интервал", value=f"{self.interval_minutes} мин", inline=True)
        embed.add_field(name="Текущий сезон", value=get_season_name(season), inline=True)
        embed.add_field(name="Время суток", value=night_status, inline=True)
        embed.add_field(name="Часовой пояс", value=f"UTC{TIMEZONE_OFFSET:+d}", inline=True)
        embed.add_field(
            name="🕐 Время бота",
            value=f"Локальное: `{now_local.strftime('%H:%M')}`\nUTC: `{now_utc.strftime('%H:%M')}`",
            inline=False
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @auto_group.sub_command(name="отправить", description="Отправить автосообщение прямо сейчас (тест)")
    async def send_now(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        success = await self.auto_message()
        if success:
            await inter.edit_original_response(content="✅ Сообщение отправлено!")
        else:
            await inter.edit_original_response(content="❌ Не удалось отправить сообщение: " + (self._last_send_error or "неизвестная ошибка"))

    @auto_group.sub_command(name="канал", description="Установить канал для автосообщений")
    async def set_channel(self, inter: disnake.ApplicationCommandInteraction, канал: disnake.TextChannel):
        self.channel_id = канал.id
        await set_setting("auto_message_channel_id", str(канал.id))
        await inter.response.send_message(
            f"✅ Канал: {канал.mention}\nНастройка сохранена в базе данных.",
            ephemeral=True
        )

    @auto_group.sub_command(name="интервал", description="Установить интервал (в минутах)")
    async def set_interval(
        self,
        inter: disnake.ApplicationCommandInteraction,
        минуты: int = commands.Param(ge=5, le=1440)
    ):
        self.interval_minutes = минуты
        await set_setting("auto_message_interval", str(минуты))
        self.auto_message.change_interval(minutes=минуты)
        await inter.response.send_message(
            f"✅ Интервал: **{минуты} мин**.\nНастройка сохранена в базе данных.",
            ephemeral=True
        )


def setup(bot: commands.InteractionBot):
    bot.add_cog(AutoMessages(bot))