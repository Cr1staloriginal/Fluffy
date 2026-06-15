import disnake
from disnake.ext import commands
import random
import datetime
import asyncio
from database import get_random_phrase
from utils.colors import main_color, accent_color

MOSCOW_TZ = datetime.timezone(datetime.timedelta(hours=3))

class UserCommands(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    # ====================== ГРУППА: ФУРРИ ======================
    @commands.slash_command(name="фурри", description="🐾 Набор фурри-команд для взаимодействия")
    async def furry(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @furry.sub_command(name="вилять", description="🐕 Вильнуть хвостом")
    async def wag(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} виляет хвостом! 🐕✨",
            f"{inter.author.mention} радостно виляет хвостиком! 🐾",
            f"{inter.author.mention} машет хвостом как пропеллером! 🌀🐕",
            f"{inter.author.mention} хвост ходит ходуном от счастья! 🥰",
            f"{inter.author.mention} пушистый хвост описывает круги в воздухе! 🌪️",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="мурчать", description="😸 Замурчать от удовольствия")
    async def purr(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} мурчит как довольный котик! 🐱💤",
            f"{inter.author.mention} издаёт глубокое урчание... мрррр! 😻",
            f"{inter.author.mention} сворачивается клубочком и мурлычет! 🧶",
            f"{inter.author.mention} мурчит так громко, что слышно на весь сервер! 🔊🐱",
            f"{inter.author.mention} трётся головой о вас и мурлычет! 💕",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="лаять", description="🐺 Гавкнуть")
    async def bark(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} громко гавкает: Гав-гав! 🐕",
            f"{inter.author.mention} лает на почтальона! 📬🐕",
            f"{inter.author.mention} издаёт короткий лай: Аф!",
            f"{inter.author.mention} заливисто лает, требуя внимания! 🗣️",
            f"{inter.author.mention} подаёт голос, чтобы предупредить о чужаках! 🚨",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="выть", description="🌕 Поволчьи на луну")
    async def howl(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} воет на луну: Ауууу! 🌕🐺",
            f"{inter.author.mention} поднимает морду и издаёт протяжный вой...",
            f"{inter.author.mention} зовёт стаю тоскливым воем! 🐾",
            f"{inter.author.mention} воет вместе с ветром, грустно смотря вдаль. 🍂",
            f"{inter.author.mention} исполняет волчью серенаду для всей луны! 🎵",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="почесать", description="🐾 Почесать за ушком (себя или друга)")
    async def scratch(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        if target == inter.author:
            responses = [
                f"{inter.author.mention} чешет себя за ушком и довольно жмурится! 🐕",
                f"{inter.author.mention} царапает лапкой за ухом... блаженство! 😌",
                f"{inter.author.mention} чешет затылок и лениво зевает. 🥱",
            ]
        else:
            responses = [
                f"{inter.author.mention} чешет {target.mention} за ушком! {target.mention} мурчит от удовольствия 🐱",
                f"{inter.author.mention} почёсывает {target.mention} — теперь {target.mention} пушистый и счастливый! 🐾",
                f"{inter.author.mention} нежно чешет {target.mention} под подбородком — тот тает! ☁️",
            ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="обнюхать", description="👃 Обнюхать участника (фурри-приветствие)")
    async def sniff(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        responses = [
            f"{inter.author.mention} осторожно обнюхивает {member.mention}! 👃🐕",
            f"{inter.author.mention} тычется носом в {member.mention} — новый знакомый! 🐾",
            f"{inter.author.mention} и {member.mention} обмениваются запахами, виляя хвостами.",
            f"{inter.author.mention} принюхивается к {member.mention} и одобрительно кивает.",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="лизнуть", description="👅 Лизнуть друга")
    async def lick(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} пытается лизнуть себя, но не достаёт языком! 👅😂")
        else:
            responses = [
                f"{inter.author.mention} лижет {member.mention} в щёчку! 💋🐶",
                f"{inter.author.mention} проводит языком по {member.mention} — приветствие принято! 🐺",
                f"{inter.author.mention} облизывает нос {member.mention}! Весело! 😜",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="играть", description="🎾 Поиграть с участником")
    async def play(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} играет сам с собой... но это не так весело! 🎾")
        else:
            responses = [
                f"{inter.author.mention} приносит мячик {member.mention}! Бросай! 🎾🐕",
                f"{inter.author.mention} и {member.mention} гоняются друг за другом по поляне! 🐾",
                f"{inter.author.mention} виляет хвостом, приглашая {member.mention} поиграть в догонялки! 🏃‍♂️",
                f"{inter.author.mention} и {member.mention} играют в перетягивание каната! 🪢",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="укусить", description="🦷 Легко укусить друга (игра)")
    async def bite(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} кусает себя за хвост — ой! 🐕😖")
        else:
            responses = [
                f"{inter.author.mention} легонько кусает {member.mention} за ушко! 🦷🐶",
                f"{inter.author.mention} нежно покусывает {member.mention} во время игры! 🐺",
                f"{inter.author.mention} хватает {member.mention} за лапу и убегает! 🏃‍♂️",
                f"{inter.author.mention} игриво кусает {member.mention} за пятку! 😈",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="обнимать", description="🤗 Обнять по-фурри-дружески")
    async def furry_hug(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} обнимает себя... и ему тепло! 🫂")
        else:
            responses = [
                f"{inter.author.mention} обнимает {member.mention} и прижимается пушистым боком! 🤗",
                f"{inter.author.mention} и {member.mention} обмениваются тёплыми объятиями! 💞",
                f"{inter.author.mention} крепко-крепко обнимает {member.mention}, не желая отпускать! 🥹",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="утешить", description="🤗 Утешить друга")
    async def comfort(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} пытается утешить себя сам, но ему грустно... 😢")
        else:
            responses = [
                f"{inter.author.mention} нежно обнимает {member.mention} и говорит, что всё будет хорошо. 🤗💕",
                f"{inter.author.mention} дарит {member.mention} горячий шоколад и пушистые объятия! ☕🧸",
                f"{inter.author.mention} гладит {member.mention} по голове и шепчет тёплые слова. 🫂",
                f"{inter.author.mention} приносит {member.mention} плед и угощает печеньем. 🍪",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="спать", description="😴 Свернуться калачиком и уснуть")
    async def sleep(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} сворачивается клубочком и засыпает... 😴💤",
            f"{inter.author.mention} зевает, укладывается на подушку и проваливается в сон.",
            f"{inter.author.mention} прячет нос под хвост и мирно посапывает. 🐾",
            f"{inter.author.mention} засыпает, мурлыча во сне. 🐱💤",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="прыгнуть", description="🐇 Прыгнуть от радости")
    async def jump(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} подпрыгивает на месте от восторга! 🐇✨",
            f"{inter.author.mention} делает высокий прыжок и приземляется на мягкие лапки.",
            f"{inter.author.mention} скачет как зайчик! 🐾",
            f"{inter.author.mention} подпрыгивает и ловит лапками воображаемую бабочку! 🦋",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="фыркнуть", description="😤 Фыркнуть с недовольством")
    async def snort(self, inter: disnake.ApplicationCommandInteraction):
        responses = [
            f"{inter.author.mention} фыркает и отворачивается! 😤",
            f"{inter.author.mention} недовольно фыркает: "Пфф!",
            f"{inter.author.mention} вздыбливает шерсть и фыркает! 🐱💢",
            f"{inter.author.mention} втягивает нос и презрительно фыркает.",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="уйти", description="🚪 Объявить, что вы отходите")
    async def leave(self, inter: disnake.ApplicationCommandInteraction, причина: str = "ненадолго"):
        responses = [
            f"{inter.author.mention} уходит {причина}. Скоро вернётся! 🚪",
            f"{inter.author.mention} машет лапкой и отправляется {причина}.",
            f"{inter.author.mention} покидает беседу ({причина}). Возвращайтесь скорее!",
        ]
        await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="покормить", description="🍲 Покормить участника")
    async def feed(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        food = ["сочное яблоко 🍎", "ароматный суп 🥣", "блюдо с рыбой 🐟", "миску каши 🥣", "вкусное печенье 🍪"]
        item = random.choice(food)
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} съел {item} и наелся до отвала!")
        else:
            await inter.response.send_message(f"{inter.author.mention} угощает {member.mention} {item}. Приятного аппетита!")

    @furry.sub_command(name="подарок", description="🎁 Сделать случайный подарок участнику")
    async def gift(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        gifts = ["пушистую игрушку 🧸", "букет полевых цветов 🌼", "звёздочку с неба ✨", "коробку конфет 🍬", "открытку[...]
        present = random.choice(gifts)
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} дарит себе {present}. Сам себя не похвалишь...")
        else:
            await inter.response.send_message(f"{inter.author.mention} дарит {member.mention} {present}! 🎁")

    @furry.sub_command(name="съесть", description="🍽️ Съесть другого участника (в шутку)")
    async def eat(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        if member == inter.author:
            await inter.response.send_message(f"{inter.author.mention} попытался съесть себя, но понял, что это невозможно! 🤔")
        else:
            responses = [
                f"{inter.author.mention} с удовольствием съел {member.mention}! 🍽️ Очень вкусно!",
                f"{inter.author.mention} проглотил {member.mention} целиком! 😋",
                f"{inter.author.mention} откусил кусочек от {member.mention} и довольно замурчал! 🐱",
                f"{inter.author.mention} съел {member.mention} и облизнулся! 👅",
                f"{inter.author.mention} быстро умял {member.mention} – тот даже пискнуть не успел! ⚡",
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="облизать", description="👅 Облизать друга")
    async def lick_enhanced(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        if target == inter.author:
            await inter.response.send_message(f"{inter.author.mention} облизывает свою лапку! 👅")
        else:
            responses = [
                f"{inter.author.mention} облизывает {target.mention}! 👅",
                f"{inter.author.mention} проводит языком по щеке {target.mention}! 🐶"
            ]
            await inter.response.send_message(random.choice(responses))

    @furry.sub_command(name="имя_фурсоны", description="🏷️ Сгенерировать случайное имя для фурсоны")
    async def fursona_name(self, inter: disnake.ApplicationCommandInteraction):
        prefixes = ["Пушист", "Мохнат", "Хвостат", "Злат", "Серебр", "Огне", "Ледяной", "Мягколап"]
        suffixes = ["хвост", "лап", "зуб", "грив", "шёрст", "крыл", "ух"]
        name = random.choice(prefixes) + random.choice(suffixes) + random.choice(["", "ик", "ка", "ок", "иш"])
        await inter.response.send_message(f"🏷️ Предлагаю имя для твоей фурсоны: **{name.capitalize()}**")

    @furry.sub_command(name="фурсона", description="🎭 Сгенерировать случайную фурсону")
    async def fursona(self, inter: disnake.ApplicationCommandInteraction):
        species = ["волк", "лиса", "кошка", "собака", "дракон", "енот", "кролик", "медведь", "птица", "олень", "фелин", "канид"]
        color = ["серебристый", "огненно-рыжий", "голубой", "фиолетовый", "белоснежный", "чёрный как смоль", "золотистый[...]
        trait = ["длинный пушистый хвост", "острые уши", "мягкие лапки", "блестящая шерсть", "добрые глаза", "пушистые щ[...]
        s = random.choice(species)
        c = random.choice(color)
        t = random.choice(trait)
        result = f"{inter.author.mention} представляет свою фурсону: **{c} {s}** с {t}! 🐾✨"
        await inter.response.send_message(result)

    # ====================== ГРУППА: ИНФОРМАЦИЯ ======================
    @commands.slash_command(name="инфо", description="ℹ️ Информационные команды")
    async def info(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @info.sub_command(name="аватар", description="🖼️ Показать аватар пользователя")
    async def avatar(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        user = member or inter.author
        embed = disnake.Embed(
            title=f"Аватар {user.display_name}",
            color=main_color(),
        )
        embed.set_image(url=user.display_avatar.url)
        await inter.response.send_message(embed=embed)

    @info.sub_command(name="сервер", description="📊 Информация о сервере")
    async def server_info(self, inter: disnake.ApplicationCommandInteraction):
        guild = inter.guild
        if not guild:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return
        embed = disnake.Embed(
            title=guild.name,
            description=guild.description or "Нет описания",
            color=main_color(),
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

    @info.sub_command(name="пользователь", description="👤 Подробная информация о пользователе")
    async def user_info(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        import aiosqlite
        from database import DB_PATH
        target = member or inter.author
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT messages_sent, voice_minutes, cookies_received FROM users WHERE user_id = ?", (target.id,)) as cur:
                row = await cur.fetchone()
        messages = row[0] if row else 0
        voice = row[1] if row else 0
        cookies = row[2] if row else 0

    @info.sub_command(name="топ", description="🏆 Топ участников по активности")
    async def leaderboard(self, inter: disnake.ApplicationCommandInteraction, 
                          тип: str = commands.Param(choices=["сообщения", "голос", "печеньки"])):
        import aiosqlite
        from database import DB_PATH
        async with aiosqlite.connect(str(DB_PATH)) as db:
            if тип == "сообщения":
                order = "messages_sent DESC"
                title = "📝 Топ по сообщениям"
                unit = "сообщ."
                field = "messages_sent"
            elif тип == "голос":
                order = "voice_minutes DESC"
                title = "🎤 Топ по голосовым минутам"
                unit = "мин."
                field = "voice_minutes"
            else:
                order = "cookies_received DESC"
                title = "🍪 Топ по печенькам"
                unit = "🍪"
                field = "cookies_received"
            async with db.execute(f"SELECT user_id, {field} FROM users ORDER BY {order} LIMIT 10") as cur:
                rows = await cur.fetchall()
        if not rows:
            await inter.response.send_message("Нет данных.", ephemeral=True)
            return
        embed = disnake.Embed(title=title, color=main_color())
        desc = []
        for i, (user_id, value) in enumerate(rows, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            desc.append(f"{i}. **{name}** — {value} {unit}")
        embed.description = "\n".join(desc)
        await inter.response.send_message(embed=embed)

    @info.sub_command(name="время", description="🕒 Текущее время по Москве")
    async def time(self, inter: disnake.ApplicationCommandInteraction):
        now = datetime.datetime.now(MOSCOW_TZ)
        await inter.response.send_message(f"🕒 Текущее московское время: **{now.strftime('%H:%M:%S')}**")

    @info.sub_command(name="пинг", description="📡 Проверить задержку бота")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        latency_ms = round(self.bot.latency * 1000)
        await inter.response.send_message(f"🏓 Понг! Задержка: **{latency_ms} мс**")

    # ====================== ГРУППА: РАЗВЛЕЧЕНИЯ ======================
    @commands.slash_command(name="развлечения", description="🎉 Развлекательные команды")
    async def fun(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @fun.sub_command(name="мило", description="🌸 Получить милую фразу с ником участника")
    async def cute(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        phrase_template = await get_random_phrase()
        if "{nick}" in phrase_template:
            text = phrase_template.format(nick=target.display_name)
        else:
            text = f"{phrase_template} {target.display_name}"
        await inter.response.send_message(text)

    @fun.sub_command(name="комплимент", description="💖 Получить милый комплимент")
    async def compliment(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        target = member or inter.author
        compliments = [
            f"{target.mention}, у тебя самая милая улыбка! 😊",
            f"{target.mention}, твоя шерсть сегодня особенно блестит ✨",
            f"{target.mention}, ты делаешь этот сервер уютнее! 🏠",
            f"{target.mention}, твой хвост – просто загляденье! 🐕",
            f"{target.mention}, ты очень пушистый человек! 🐾",
            f"{target.mention}, твой голос звучит как песня! 🎶",
            f"{target.mention}, с тобой всегда тепло и спокойно.",
        ]
        await inter.response.send_message(random.choice(compliments))

    @fun.sub_command(name="шутка", description="😂 Случайная шутка (фурри-тематика)")
    async def joke(self, inter: disnake.ApplicationCommandInteraction):
        jokes = [
            "Почему фурри не играют в карты? Потому что волки всегда блефуют! 🃏🐺",
            "Как назвать лису с компасом? Лиси-пеленг! 🧭🦊",
            "Что говорит кот, когда ему скучно? «Мур... чай». ☕🐱",
            "Почему драконы любят Discord? Там можно пускать сообщения с огоньком! 🔥🐉",
            "Какой любимый танец у собак? Хвост-джига! 🕺🐕",
        ]
        await inter.response.send_message(random.choice(jokes))

    @fun.sub_command(name="факт", description="📖 Случайный интересный факт")
    async def fact(self, inter: disnake.ApplicationCommandInteraction):
        facts = [
            "Лисы умеют издавать около 40 разных звуков.",
            "Кошки мурлычут на частоте, которая помогает лечить кости.",
            "Волки воют не на луну, а для общения со стаей.",
            "Собаки понимают до 250 слов и жестов.",
            "Фурри-сообщество зародилось в 1980-х годах на научно-фантастических конвентах.",
            "Осьминоги имеют три сердца и голубую кровь.",
        ]
        await inter.response.send_message(f"📌 {random.choice(facts)}")

    @fun.sub_command(name="предсказание", description="🔮 Бот предскажет ваше будущее")
    async def fortune(self, inter: disnake.ApplicationCommandInteraction):
        fortunes = [
            "🐾 Скоро ты встретишь нового пушистого друга!",
            "🍪 Тебя ждёт вкусное угощение сегодня вечером.",
            "🎉 В ближайшие дни случится что-то неожиданно радостное.",
            "💤 Ты выспишься на выходных – обещаю!",
            "✨ Твоя фурсона станет ещё круче после обновления.",
            "🦊 Кто-то тайно хочет с тобой обняться.",
            "🌙 Лунный свет принесёт тебе вдохновение.",
            "🍬 Тебя ждёт сладкий сюрприз.",
        ]
        await inter.response.send_message(f"🔮 {random.choice(fortunes)}")

    @fun.sub_command(name="погода", description="☀️ Погода в фурри-городке")
    async def weather(self, inter: disnake.ApplicationCommandInteraction):
        weathers = [
            "☀️ Солнечно, пушистые облака, температура +24°C",
            "🌧️ Моросит дождик, но радуга уже близко",
            "🍂 Лёгкий ветерок, листья кружатся в воздухе",
            "❄️ Снегопад! Идеально для игр в сугробах",
            "🌈 После дождя – двойная радуга!",
            "🌙 Тёплая лунная ночь, звёзды мерцают.",
        ]
        await inter.response.send_message(f"{random.choice(weathers)}")

    @fun.sub_command(name="лакомство", description="🍪 Угостить себя или друга")
    async def treat(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        treats = ["печенье 🍪", "мороженое 🍦", "шоколадку 🍫", "яблоко 🍎", "пирожное 🧁", "конфету 🍬"]
        target = member or inter.author
        treat = random.choice(treats)
        if target == inter.author:
            await inter.response.send_message(f"{inter.author.mention} угощается {treat}! 🎂")
        else:
            await inter.response.send_message(f"{inter.author.mention} угощает {target.mention} {treat}! 🎁")

    @fun.sub_command(name="викторина", description="🧠 Случайный вопрос (про фурри)")
    async def quiz(self, inter: disnake.ApplicationCommandInteraction):
        questions = [
            ("Как называется furry-сообщество в России?", "РуФурри"),
            ("Что означает слово 'фурсона'?", "Антропоморфный персонаж"),
            ("Какой зверь чаще всего выбирается фурсонами?", "Волк"),
            ("Что такое 'свит' в фурри-тусовке?", "Милый и дружелюбный персонаж"),
            ("Кто придумал термин 'furry'?", "Марк Мерлино"),
        ]
        q, correct = random.choice(questions)
        await inter.response.send_message(f"❓ **{q}**\n*Правильный ответ будет через 15 секунд...*")
        await asyncio.sleep(15)
        await inter.followup.send(f"✅ Правильный ответ: **{correct}**")

    @fun.sub_command(name="таро", description="🔮 Вытянуть карту Таро")
    async def tarot(self, inter: disnake.ApplicationCommandInteraction):
        cards = [
            ("Шут", "Новые начинания, спонтанность, вера в лучшее."),
            ("Маг", "Проявление желаний, сила воли, навыки."),
            ("Верховная Жрица", "Интуиция, тайны, внутренний голос."),
            ("Императрица", "Плодородие, материнство, изобилие."),
            ("Император", "Власть, стабильность, структура."),
            ("Влюблённые", "Любовь, выбор, гармония отношений."),
            ("Колесница", "Победа, контроль, движение вперёд."),
            ("Сила", "Мужество, терпение, внутренняя сила."),
            ("Отшельник", "Самоанализ, мудрость, поиск истины."),
            ("Колесо Фортуны", "Перемены, судьба, удача."),
            ("Справедливость", "Честность, причинность, баланс."),
            ("Повешенный", "Жертва, новое видение, приостановка."),
            ("Смерть", "Трансформация, окончание старого, новое начало."),
            ("Умеренность", "Баланс, исцеление, терпение."),
            ("Дьявол", "Привязанность, материализм, искушение."),
            ("Башня", "Крушение, внезапные перемены, откровение."),
            ("Звезда", "Надежда, вдохновение, ясность."),
            ("Луна", "Иллюзии, страхи, подсознание."),
            ("Солнце", "Радость, успех, позитив."),
            ("Суд", "Пробуждение, возрождение, подведение итогов."),
            ("Мир", "Завершение, исполнение, гармония."),
        ]
        card, meaning = random.choice(cards)
        embed = disnake.Embed(
            title=f"🔮 Карта Таро для {inter.author.display_name}",
            description=f"**{card}**\n{meaning}",
            color=disnake.Color.purple()  # оставляем фиолетовый для магии
        )
        embed.set_footer(text="Будущее не определено, доверяйте своему сердцу ❤️")
        await inter.response.send_message(embed=embed)

    @fun.sub_command(name="посоветовать", description="🎱 Задать вопрос и получить ответ")
    async def advise(self, inter: disnake.ApplicationCommandInteraction, вопрос: str):
        answers = [
            "Безусловно!", "Определённо да.", "Мой источник говорит, что да.", "Знаки указывают на да.",
            "Скорее да, чем нет.", "Пока не ясно, попробуй позже.", "Не могу сказать сейчас.",
            "Лучше не отвечать, чтобы не сглазить.", "Спроси что-то другое.", "Однозначно нет.",
            "Я бы не советовал.", "Отрицательно.", "Шансы невелики.", "Даже не думай.",
            "Ты сам знаешь ответ.", "Мур... (что значит 'да')", "Фыр! (категорическое нет)",
        ]
        answer = random.choice(answers)
        embed = disnake.Embed(
            title="🎱 Магический пушистый шар",
            description=f"**Вопрос:** {вопрос}\n**Ответ:** {answer}",
            color=main_color()
        )
        await inter.response.send_message(embed=embed)

    # ====================== ГРУППА: ИГРЫ ======================
    @commands.slash_command(name="игры", description="🎮 Игры с ботом")
    async def games(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @games.sub_command(name="рандом", description="🎲 Случайное число от A до B")
    async def random_number(self, inter: disnake.ApplicationCommandInteraction, от: int = 1, до: int = 100):
        if от > до:
            await inter.response.send_message("❌ Число 'от' не может быть больше 'до'.", ephemeral=True)
            return
        result = random.randint(от, до)
        await inter.response.send_message(f"🎲 Случайное число от {от} до {до}: **{result}**")

    @games.sub_command(name="монетка", description="🪙 Подбросить монетку")
    async def coin(self, inter: disnake.ApplicationCommandInteraction):
        result = random.choice(["орёл", "решка"])
        emoji = "🪙" if result == "орёл" else "💿"
        await inter.response.send_message(f"{emoji} Выпал **{result}**!")

    @games.sub_command(name="угадай", description="🎯 Угадай число от 1 до 10")
    async def guess(self, inter: disnake.ApplicationCommandInteraction, число: int):
        secret = random.randint(1, 10)
        if число == secret:
            await inter.response.send_message(f"🎉 {inter.author.mention}, ты угадал! Это было число {secret}!")
        else:
            await inter.response.send_message(f"❌ {inter.author.mention}, не угадал. Я загадал {secret}. Попробуй ещё!")

    @games.sub_command(name="кнб", description="✊ Камень, ножницы, бумага (игра с ботом)")
    async def rps(self, inter: disnake.ApplicationCommandInteraction, выбор: str = commands.Param(choices=["камень", "ножницы", "бумага"])):
        bot_choice = random.choice(["камень", "ножницы", "бумага"])