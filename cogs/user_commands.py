import disnake
from disnake.ext import commands
import random
import datetime
import asyncio
from database import get_random_phrase

# Московское время (UTC+3)
MOSCOW_TZ = datetime.timezone(datetime.timedelta(hours=3))

class UserCommands(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    # ====================== ФУРРИ-RP КОМАНДЫ ======================

    @commands.slash_command(name="вилять", description="🐕 Вильнуть хвостом")
    async def wag(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} виляет хвостом! 🐕✨",
            f"{inter.author.mention} радостно виляет хвостиком! 🐾",
            f"{inter.author.mention} машет хвостом как пропеллером! 🌀🐕",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="мурчать", description="😸 Замурчать от удовольствия")
    async def purr(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} мурчит как довольный котик! 🐱💤",
            f"{inter.author.mention} издаёт глубокое урчание... мрррр! 😻",
            f"{inter.author.mention} сворачивается клубочком и мурлычет! 🧶",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="лаять", description="🐺 Гавкнуть")
    async def bark(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} громко гавкает: Гав-гав! 🐕",
            f"{inter.author.mention} лает на почтальона! 📬🐕",
            f"{inter.author.mention} издаёт короткий лай: Аф!",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="выть", description="🌕 Поволчьи на луну")
    async def howl(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} воет на луну: Ауууу! 🌕🐺",
            f"{inter.author.mention} поднимает морду и издаёт протяжный вой...",
            f"{inter.author.mention} зовёт стаю тоскливым воем! 🐾",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="почесать", description="🐾 Почесать за ушком (себя или друга)")
    async def scratch(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        if target == inter.author:
            responses = [
                f"{inter.author.mention} чешет себя за ушком и довольно жмурится! 🐕",
                f"{inter.author.mention} царапает лапкой за ухом... блаженство! 😌",
            ]
        else:
            responses = [
                f"{inter.author.mention} чешет {target.mention} за ушком! {target.mention} мурчит от удовольствия 🐱",
                f"{inter.author.mention} почёсывает {target.mention} — теперь {target.mention} пушистый и счастливый! 🐾",
            ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="обнюхать", description="👃 Обнюхать участника (фурри-приветствие)")
    async def sniff(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        responses = [
            f"{inter.author.mention} осторожно обнюхивает {member.mention}! 👃🐕",
            f"{inter.author.mention} тычется носом в {member.mention} — новый знакомый! 🐾",
            f"{inter.author.mention} и {member.mention} обмениваются запахами, виляя хвостами.",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="лизнуть", description="👅 Лизнуть друга (дружеское фурри-приветствие)")
    async def lick(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} пытается лизнуть себя, но не достаёт языком! 👅😂")
        else:
            responses = [
                f"{inter.author.mention} лижет {member.mention} в щёчку! 💋🐶",
                f"{inter.author.mention} проводит языком по {member.mention} — приветствие принято! 🐺",
            ]
            await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="играть", description="🎾 Поиграть с участником")
    async def play(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} играет сам с собой... но это не так весело! 🎾")
        else:
            responses = [
                f"{inter.author.mention} приносит мячик {member.mention}! Бросай! 🎾🐕",
                f"{inter.author.mention} и {member.mention} гоняются друг за другом по поляне! 🐾",
                f"{inter.author.mention} виляет хвостом, приглашая {member.mention} поиграть в догонялки! 🏃‍♂️",
            ]
            await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="фурсона", description="🎭 Показать свою фурсону (рандомное описание)")
    async def fursona(self, inter: disnake.ApplicationCommandInteraction):
        species = ["волк", "лиса", "кошка", "собака", "дракон", "енот", "кролик", "медведь", "птица", "олень"]
        color = ["серебристый", "огненно-рыжий", "голубой", "фиолетовый", "белоснежный", "чёрный как смоль", "золотистый"]
        trait = ["длинный пушистый хвост", "острые уши", "мягкие лапки", "блестящая шерсть", "добрые глаза"]
        s = random.choice(species)
        c = random.choice(color)
        t = random.choice(trait)
        result = f"{inter.author.mention} представляет свою фурсону: **{c} {s}** с {t}! 🐾✨"
        await inter.response.send_message(result)

    @commands.slash_command(name="укусить", description="🦷 Легко укусить друга (игра)")
    async def bite(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} кусает себя за хвост — ой! 🐕😖")
        else:
            responses = [
                f"{inter.author.mention} легонько кусает {member.mention} за ушко! 🦷🐶",
                f"{inter.author.mention} нежно покусывает {member.mention} во время игры! 🐺",
            ]
            await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="спать", description="😴 Свернуться калачиком и уснуть")
    async def sleep(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} сворачивается клубочком и засыпает... 😴💤",
            f"{inter.author.mention} зевает, укладывается на подушку и проваливается в сон.",
            f"{inter.author.mention} прячет нос под хвост и мирно посапывает. 🐾",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="прыгнуть", description="🐇 Прыгнуть от радости")
    async def jump(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} подпрыгивает на месте от восторга! 🐇✨",
            f"{inter.author.mention} делает высокий прыжок и приземляется на мягкие лапки.",
            f"{inter.author.mention} скачет как зайчик! 🐾",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="фыркнуть", description="😤 Фыркнуть с недовольством")
    async def snort(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} фыркает и отворачивается! 😤",
            f"{inter.author.mention} недовольно фыркает: \"Пфф!\"",
            f"{inter.author.mention} вздыбливает шерсть и фыркает! 🐱💢",
        ]
        await inter.response.send_message(random.choice(responses))

    @commands.slash_command(name="обнимать", description="🤗 Обнять по-фурри-дружески")
    async def furry_hug(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} обнимает себя... и ему тепло! 🫂")
        else:
            responses = [
                f"{inter.author.mention} обнимает {member.mention} и прижимается пушистым боком! 🤗",
                f"{inter.author.mention} и {member.mention} обмениваются тёплыми объятиями! 💞",
            ]
            await inter.response.send_message(random.choice(responses))

    # ====================== ПОЛЕЗНЫЕ КОМАНДЫ ======================

    @commands.slash_command(name="мило", description="🌸 Получить милую фразу с ником участника")
    async def cute(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        phrase_template = await get_random_phrase()
        if "{nick}" in phrase_template:
            text = phrase_template.format(nick=target.display_name)
        else:
            text = f"{phrase_template} {target.display_name}"
        await inter.response.send_message(text)

    @commands.slash_command(name="аватар", description="🖼️ Показать аватар пользователя")
    async def avatar(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        user = member or inter.author
        embed = disnake.Embed(
            title=f"Аватар {user.display_name}",
            color=disnake.Color.blurple(),
        )
        embed.set_image(url=user.display_avatar.url)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="сервер", description="📊 Информация о сервере")
    async def server_info(self, inter: disnake.ApplicationCommandInteraction):
        guild = inter.guild
        if not guild:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return
        embed = disnake.Embed(
            title=guild.name,
            description=guild.description or "Нет описания",
            color=disnake.Color.green(),
            timestamp=disnake.utils.utcnow()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👑 Владелец", value=guild.owner.mention if guild.owner else "Неизвестно", inline=True)
        embed.add_field(name="👥 Участников", value=guild.member_count, inline=True)
        embed.add_field(name="💬 Каналов", value=len(guild.channels), inline=True)
        embed.add_field(name="📅 Создан", value=disnake.utils.format_dt(guild.created_at, "R"), inline=True)
        embed.add_field(name="🚀 Уровень буста", value=guild.premium_tier, inline=True)
        embed.add_field(name="🔖 ID", value=guild.id, inline=True)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="пользователь", description="👤 Информация о пользователе")
    async def user_info(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        embed = disnake.Embed(
            title=target.display_name,
            color=target.color if target.color else disnake.Color.blurple(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🆔 ID", value=target.id, inline=True)
        embed.add_field(name="🤖 Бот", value="Да" if target.bot else "Нет", inline=True)
        embed.add_field(name="📅 Аккаунт создан", value=disnake.utils.format_dt(target.created_at, "R"), inline=False)
        if isinstance(target, disnake.Member) and target.joined_at:
            embed.add_field(name="📥 Присоединился", value=disnake.utils.format_dt(target.joined_at, "R"), inline=False)
            top_role = target.top_role if target.top_role.name != "@everyone" else None
            if top_role:
                embed.add_field(name="⭐ Высшая роль", value=top_role.mention, inline=True)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="рандом", description="🎲 Случайное число от A до B")
    async def random_number(self, inter: disnake.ApplicationCommandInteraction, от: int = 1, до: int = 100):
        if от > до:
            await inter.response.send_message("❌ Число 'от' не может быть больше 'до'.", ephemeral=True)
            return
        result = random.randint(от, до)
        await inter.response.send_message(f"🎲 Случайное число от {от} до {до}: **{result}**")

    @commands.slash_command(name="монетка", description="🪙 Подбросить монетку (орёл или решка)")
    async def coin(self, inter: disnake.ApplicationCommandInteraction):
        result = random.choice(["орёл", "решка"])
        emoji = "🪙" if result == "орёл" else "💿"
        await inter.response.send_message(f"{emoji} Выпал **{result}**!")

    @commands.slash_command(name="время", description="🕒 Текущее время по Москве")
    async def time(self, inter: disnake.ApplicationCommandInteraction):
        now = datetime.datetime.now(MOSCOW_TZ)
        await inter.response.send_message(f"🕒 Текущее московское время: **{now.strftime('%H:%M:%S')}**")

    @commands.slash_command(name="бип", description="📡 Проверить задержку бота (пинг)")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        latency_ms = round(self.bot.latency * 1000)
        await inter.response.send_message(f"🏓 Понг! Задержка: **{latency_ms} мс**")

    # ====================== ИГРЫ И РАЗВЛЕЧЕНИЯ ======================

    @commands.slash_command(name="угадай", description="🎯 Угадай число от 1 до 10")
    async def guess(self, inter: disnake.ApplicationCommandInteraction, число: int):
        secret = random.randint(1, 10)
        if число == secret:
            await inter.response.send_message(f"🎉 {inter.author.mention}, ты угадал! Это было число {secret}!")
        else:
            await inter.response.send_message(f"❌ {inter.author.mention}, не угадал. Я загадал {secret}. Попробуй ещё!")

    @commands.slash_command(name="кнб", description="✊ Камень, ножницы, бумага (игра с ботом)")
    async def rps(self, inter: disnake.ApplicationCommandInteraction, выбор: str = commands.Param(choices=["камень", "ножницы", "бумага"])):
        bot_choice = random.choice(["камень", "ножницы", "бумага"])
        emojis = {"камень": "🪨", "ножницы": "✂️", "бумага": "📄"}
        if выбор == bot_choice:
            result = "Ничья!"
        elif (выбор == "камень" and bot_choice == "ножницы") or (выбор == "ножницы" and bot_choice == "бумага") or (выбор == "бумага" and bot_choice == "камень"):
            result = "Ты выиграл!"
        else:
            result = "Я выиграл!"
        await inter.response.send_message(f"{emojis[выбор]} ты показал {выбор}\n{emojis[bot_choice]} бот показал {bot_choice}\n**{result}**")

    @commands.slash_command(name="викторина", description="🧠 Случайный вопрос (про фурри)")
    async def quiz(self, inter: disnake.ApplicationCommandInteraction):
        questions = [
            ("Как называется furry-сообщество в России?", "РуФурри"),
            ("Что означает слово 'фурсона'?", "Антропоморфный персонаж"),
            ("Какой зверь чаще всего выбирается фурсонами?", "Волк"),
            ("Что такое 'свит' в фурри-тусовке?", "Милый и дружелюбный персонаж"),
        ]
        q, correct = random.choice(questions)
        await inter.response.send_message(f"❓ **{q}**\n*Правильный ответ будет через 15 секунд...*")
        await asyncio.sleep(15)
        await inter.followup.send(f"✅ Правильный ответ: **{correct}**")

    @commands.slash_command(name="предсказание", description="🔮 Бот предскажет ваше будущее")
    async def fortune(self, inter: disnake.ApplicationCommandInteraction):
        fortunes = [
            "🐾 Скоро ты встретишь нового пушистого друга!",
            "🍪 Тебя ждёт вкусное угощение сегодня вечером.",
            "🎉 В ближайшие дни случится что-то неожиданно радостное.",
            "💤 Ты выспишься на выходных – обещаю!",
            "✨ Твоя фурсона станет ещё круче после обновления.",
            "🦊 Кто-то тайно хочет с тобой обняться.",
            "🌙 Лунный свет принесёт тебе вдохновение.",
        ]
        await inter.response.send_message(f"🔮 {random.choice(fortunes)}")

    @commands.slash_command(name="комплимент", description="💖 Получить милый комплимент")
    async def compliment(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        compliments = [
            f"{target.mention}, у тебя самая милая улыбка! 😊",
            f"{target.mention}, твоя шерсть сегодня особенно блестит ✨",
            f"{target.mention}, ты делаешь этот сервер уютнее! 🏠",
            f"{target.mention}, твой хвост – просто загляденье! 🐕",
            f"{target.mention}, ты очень пушистый человек! 🐾",
        ]
        await inter.response.send_message(random.choice(compliments))

    @commands.slash_command(name="шутка", description="😂 Случайная шутка (фурри-тематика)")
    async def joke(self, inter: disnake.ApplicationCommandInteraction):
        jokes = [
            "Почему фурри не играют в карты? Потому что волки всегда блефуют! 🃏🐺",
            "Как назвать лису с компасом? Лиси-пеленг! 🧭🦊",
            "Что говорит кот, когда ему скучно? «Мур... чай». ☕🐱",
            "Почему драконы любят Discord? Там можно пускать сообщения с огоньком! 🔥🐉",
        ]
        await inter.response.send_message(random.choice(jokes))

    @commands.slash_command(name="факт", description="📖 Случайный интересный факт")
    async def fact(self, inter: disnake.ApplicationCommandInteraction):
        facts = [
            "Лисы умеют издавать около 40 разных звуков.",
            "Кошки мурлычут на частоте, которая помогает лечить кости.",
            "Волки воют не на луну, а для общения со стаей.",
            "Собаки понимают до 250 слов и жестов.",
            "Фурри-сообщество зародилось в 1980-х годах на научно-фантастических конвентах.",
        ]
        await inter.response.send_message(f"📌 {random.choice(facts)}")

    @commands.slash_command(name="имя_фурсоны", description="🏷️ Сгенерировать случайное имя для фурсоны")
    async def fursona_name(self, inter: disnake.ApplicationCommandInteraction):
        prefixes = ["Пушист", "Мохнат", "Хвостат", "Злат", "Серебр", "Огне", "Ледяной"]
        suffixes = ["хвост", "лап", "зуб", "грив", "шёрст", "крыл"]
        name = random.choice(prefixes) + random.choice(suffixes) + random.choice(["", "ик", "ка", "ок"])
        await inter.response.send_message(f"🏷️ Предлагаю имя для твоей фурсоны: **{name.capitalize()}**")

    @commands.slash_command(name="погода", description="☀️ Погода в фурри-городке (фантазия)")
    async def weather(self, inter: disnake.ApplicationCommandInteraction):
        weathers = [
            "☀️ Солнечно, пушистые облака, температура +24°C",
            "🌧️ Моросит дождик, но радуга уже близко",
            "🍂 Лёгкий ветерок, листья кружатся в воздухе",
            "❄️ Снегопад! Идеально для игр в сугробах",
            "🌈 После дождя – двойная радуга!",
        ]
        await inter.response.send_message(f"{random.choice(weathers)}")

    @commands.slash_command(name="лакомство", description="🍪 Угостить себя или друга случайным лакомством")
    async def treat(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        treats = ["печенье 🍪", "мороженое 🍦", "шоколадку 🍫", "яблоко 🍎", "пирожное 🧁"]
        target = member or inter.author
        treat = random.choice(treats)
        if target == inter.author:
            await inter.response.send_message(f"{inter.author.mention} угощается {treat}! 🎂")
        else:
            await inter.response.send_message(f"{inter.author.mention} угощает {target.mention} {treat}! 🎁")

def setup(bot: commands.InteractionBot):
    bot.add_cog(UserCommands(bot))