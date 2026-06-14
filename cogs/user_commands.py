# cogs/user_commands.py

import disnake
from disnake.ext import commands
import random
import datetime
import asyncio
from database import get_random_phrase

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

    @furry.sub_command(name="фурсона", description="🎭 Сгенерировать случайную фурсону")
    async def fursona(self, inter: disnake.ApplicationCommandInteraction):
        species = ["волк", "лиса", "кошка", "собака", "дракон", "енот", "кролик", "медведь", "птица", "олень", "фелин", "канид"]
        color = ["серебристый", "огненно-рыжий", "голубой", "фиолетовый", "белоснежный", "чёрный как смоль", "золотистый", "розовый", "лавандовый"]
        trait = ["длинный пушистый хвост", "острые уши", "мягкие лапки", "блестящая шерсть", "добрые глаза", "пушистые щёки", "серёжки на ушах"]
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
            color=disnake.Color.blurple(),
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

    @info.sub_command(name="пользователь", description="👤 Информация о пользователе")
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
    async fun(self, inter: disnake.ApplicationCommandInteraction):
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

    # ====================== ГРУППА: ИГРЫ ======================
    @commands.slash_command(name="игры", description="🎮 Игры с ботом")
    async games(self, inter: disnake.ApplicationCommandInteraction):
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
        emojis = {"камень": "🪨", "ножницы": "✂️", "бумага": "📄"}
        if выбор == bot_choice:
            result = "Ничья!"
        elif (выбор == "камень" and bot_choice == "ножницы") or (выбор == "ножницы" and bot_choice == "бумага") or (выбор == "бумага" and bot_choice == "камень"):
            result = "Ты выиграл!"
        else:
            result = "Я выиграл!"
        await inter.response.send_message(f"{emojis[выбор]} ты показал {выбор}\n{emojis[bot_choice]} бот показал {bot_choice}\n**{result}**")

    @games.sub_command(name="кость", description="🎲 Бросить игральную кость (1-6)")
    async def roll_dice(self, inter: disnake.ApplicationCommandInteraction):
        result = random.randint(1, 6)
        await inter.response.send_message(f"{inter.author.mention} бросает кость... Выпало **{result}**! 🎲")

def setup(bot: commands.InteractionBot):
    bot.add_cog(UserCommands(bot))