import disnake
from disnake.ext import commands, tasks
import datetime
import random
import os
from utils.seasons import get_current_season, get_season_name


class AutoMessages(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.channel_id = int(os.getenv("AUTO_MESSAGE_CHANNEL_ID", 0))
        self.interval_minutes = int(os.getenv("AUTO_MESSAGE_INTERVAL", 60))  # по умолчанию 1 час
        self.min_delay = int(os.getenv("AUTO_MESSAGE_MIN_DELAY", 0))  # минимальная задержка в минутах
        self.enabled = os.getenv("AUTO_MESSAGE_ENABLED", "true").lower() == "true"

        # ===== ДНЕВНЫЕ СООБЩЕНИЯ (по сезонам) =====
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

        # Запускаем задачу, если включено
        if self.enabled:
            self.auto_message.start()
        else:
            print("[AutoMessages] Автосообщения отключены в .env")

    def cog_unload(self):
        if self.auto_message.is_running():
            self.auto_message.cancel()

    @tasks.loop(minutes=60)
    async def auto_message(self):
        # Обновляем интервал, если он изменился в .env
        if self.auto_message.minutes != self.interval_minutes:
            self.auto_message.change_interval(minutes=self.interval_minutes)

        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print(f"[AutoMessages] Канал {self.channel_id} не найден")
            return

        # Определяем время суток
        now = datetime.datetime.now()
        hour = now.hour
        # Ночное время: с 23:00 до 6:00
        if hour >= 23 or hour < 6:
            msg = random.choice(self.messages_night)
        else:
            season = get_current_season()
            messages = self.messages_day.get(season, self.messages_day["default"])
            msg = random.choice(messages)

        text = msg.format(bot=self.bot.user.display_name)

        try:
            await channel.send(text)
            print(f"[AutoMessages] Отправлено: {text}")
        except Exception as e:
            print(f"[AutoMessages] Ошибка отправки: {e}")

    @auto_message.before_loop
    async def before_auto_message(self):
        await self.bot.wait_until_ready()
        # Небольшая случайная задержка перед первым сообщением
        if self.min_delay > 0:
            delay = random.randint(0, self.min_delay * 60)
            print(f"[AutoMessages] Первое сообщение через {delay // 60} мин {delay % 60} сек")
            await asyncio.sleep(delay)
        print("[AutoMessages] Задача автоматических сообщений запущена")

    # ===== КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА =====
    @commands.slash_command(name="автосообщение", description="⚙️ Управление автосообщениями (только для администраторов)")
    @commands.has_permissions(administrator=True)
    async def auto_group(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @auto_group.sub_command(name="статус", description="Показать статус автосообщений")
    async def status(self, inter: disnake.ApplicationCommandInteraction):
        channel = self.bot.get_channel(self.channel_id)
        channel_text = channel.mention if channel else "❌ не найден"

        season = get_current_season()
        running = "✅ Включены" if self.auto_message.is_running() else "❌ Выключены"

        embed = disnake.Embed(
            title="📢 Автосообщения",
            color=disnake.Color.blurple()
        )
        embed.add_field(name="Статус", value=running, inline=True)
        embed.add_field(name="Канал", value=channel_text, inline=True)
        embed.add_field(name="Интервал", value=f"{self.interval_minutes} мин", inline=True)
        embed.add_field(name="Текущий сезон", value=get_season_name(season), inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @auto_group.sub_command(name="отправить", description="Отправить автосообщение прямо сейчас (для теста)")
    async def send_now(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        await self.auto_message()
        await inter.edit_original_response(content="✅ Сообщение отправлено!")

    @auto_group.sub_command(name="канал", description="Установить канал для автосообщений")
    async def set_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        канал: disnake.TextChannel
    ):
        self.channel_id = канал.id
        await inter.response.send_message(
            f"✅ Канал для автосообщений установлен: {канал.mention}\n"
            f"⚠️ Не забудьте добавить `AUTO_MESSAGE_CHANNEL_ID={канал.id}` в `.env`.",
            ephemeral=True
        )

    @auto_group.sub_command(name="интервал", description="Установить интервал автосообщений (в минутах)")
    async def set_interval(
        self,
        inter: disnake.ApplicationCommandInteraction,
        минуты: int = commands.Param(ge=5, le=1440)
    ):
        self.interval_minutes = минуты
        if self.auto_message.is_running():
            self.auto_message.change_interval(minutes=минуты)
        await inter.response.send_message(
            f"✅ Интервал изменён на **{минуты} мин**.\n"
            f"⚠️ Для сохранения добавьте `AUTO_MESSAGE_INTERVAL={минуты}` в `.env`.",
            ephemeral=True
        )


import asyncio  # нужен для before_loop


def setup(bot: commands.InteractionBot):
    bot.add_cog(AutoMessages(bot))