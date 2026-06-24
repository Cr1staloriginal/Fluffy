import disnake
from disnake.ext import commands
import os
import re
import time
from collections import defaultdict
from database import add_warn

# ---------------------- ИГНОРИРУЕМЫЕ КАНАЛЫ ----------------------
# Игнорируемые по ID (точное совпадение)
IGNORED_CHANNEL_IDS = [1473318583089234022, 1473324895546114324, 1473323793517772853, 1473324108791152794, 1473336508835434707, 1473333063760089149, 1473333954059964418, 1518685822268997744, 1436317914386010195 ]

# ---------------------- ПУТИ К ФАЙЛАМ (опционально) ----------------------
WORDS_FILE = os.path.join(os.path.dirname(__file__), "..", "words.txt")
SCAM_DOMAINS_FILE = os.path.join(os.path.dirname(__file__), "..", "scam_domains.txt")
POLITICS_WORDS_FILE = os.path.join(os.path.dirname(__file__), "..", "politics_words.txt")

# ---------------------- ВСТРОЕННЫЕ СПИСКИ (максимальное покрытие) ----------------------

# 1. ЗАПРЕЩЁННЫЕ СЛОВА (мат, оскорбления, дискриминация)
BUILTIN_BAD_WORDS = [
    "бзд", "бля", "елд", "говн", "жоп", "муд", "перд", "пизд", "хуй", "шлюх", "хер", "манд", "гонд",
    "еб", "мудак", "тварь", "сук", "бляд", "блуд", "бздюх", "дроч", "ебал", "ебен", "еби", "ебн",
    "ебт", "ебич", "ебуч", "заеб", "изъеб", "наеб", "объеб", "оеб", "отъеб", "перееб", "подъеб",
    "поеб", "приеб", "проеб", "разъеб", "съеб", "уеб", "хуев", "хуин", "хуйл", "хуйн", "хуйс",
    "хуйц", "хуйч", "хуйш", "хуяк", "хуяр", "хуяс", "хуят", "пиздобол", "пиздюк", "пиздяк",
    "пиздярин", "пиздятина", "пиздячий", "блядво", "блядеха", "блядина", "блядист", "блядище",
    "блядки", "блядов", "блядский", "блядство", "блядствовать", "блядун", "блядюга", "блядюра",
    "блядюшка", "блядюшник", "дурак", "идиот", "тупой", "тупица", "дебил", "урод", "козёл", "сволочь",
    "мерзавец", "неадекват", "псих", "чокнутый", "шизоид", "шизофреник", "олигофрен", "даун",
    "имбицил", "кретин", "балбес", "болван", "дуралей", "недоумок", "придурок", "обалдуй", "олух",
    "простофиля", "растяпа", "рохля", "тюфяк", "флегма", "хам", "нахал", "грубиян", "невежа", "неуч",
    "бездарь", "посредственность", "ничтожество", "фашист", "фашизм", "расист", "расизм", "нацист",
    "нацизм", "гомофоб", "гомофобия", "ксенофоб", "ксенофобия", "черножопый", "чернозадый", "жид",
    "жидов", "хохол", "хохлы", "москаль", "москали", "чурка", "чурки", "узкоглазый", "узкоглазые",
    "гомик", "гомосек", "гомосексуалист", "лесби", "лесбиянка", "педераст", "пидор", "пидорас",
    "мудила", "мудак", "мудачьё"
]

# 2. ФИШИНГОВЫЕ И СОКРАЩЁННЫЕ ДОМЕНЫ (100+)
BUILTIN_SCAM_DOMAINS = [
    "bit.ly", "goo.gl", "tinyurl.com", "clck.ru", "is.gd", "rb.gy", "cutt.ly", "t.co",
    "gg.gg", "v.gd", "u.to", "x.co", "shorturl.at", "ow.ly", "buff.ly", "adf.ly",
    "shorte.st", "bitly.com", "tiny.cc", "url4short.com", "dis.gd", "soo.gd",
    "qr.ae", "s.id", "n9.cl", "vurl.com", "shink.in", "j.mp", "su.pr", "wp.me", "bit.do",
    "1link.in", "lnkd.in", "db.tt", "tny.im", "bc.vc", "chilp.it", "cli.gs", "cur.lv",
    "digg.com/u", "fb.me", "fd.cm", "fur.ly", "gizmo.do", "hackurls.com", "href.li",
    "huff.to", "iki.sh", "kl.am", "kutt.it", "link.tl", "lru.jp", "maper.info",
    "merky.de", "minilien.com", "moourl.com", "msft.social", "mzl.la", "n.pr",
    "nanourl.com", "not.my", "novel.li", "nowlinks.net", "o-x.fr", "om.ly",
    "on.cnn.com", "on.mktw.net", "onforb.es", "ow.gy", "p.pw", "p.tl", "pare.link",
    "pep.si", "pixly.net", "plista.com", "po.st", "post.ly", "pp.gg",
    "prettylinkpro.com", "q.gs", "qps.ru", "qr.net", "qu.tc", "qxp.ru", "r.spr.ly",
    "read.bi", "redir.ec", "ref.so", "redirect.is", "reg.vg", "reut.rs", "ri.ms",
    "s.coop", "s.id", "s7y.us", "sa.si", "scrnch.me", "short.est", "short.ie",
    "short.to", "shortlink.co.uk", "shorturl.com", "shout.to", "shrinkify.com",
    "shrinkster.com", "shrtco.de", "sina.lt", "skinn.it", "sl.ink", "slnk.eu",
    "smf.is", "sn.im", "snipr.com", "snipurl.com", "snurl.com", "sp2.ro", "spot.lt",
    "sq.co", "srnk.net", "srs.li", "surl.com.au", "t2mio.com", "ta.gd", "tagmast.er",
    "tcrn.ch", "telegra.ph", "theinventory.com", "tidd.ly", "tiny.pl",
    "tinyarrows.com", "tl.gd", "tny.com", "togoto.us", "toi.sg", "tr.im", "trk.li",
    "tru.io", "tsa.me", "tw.gs", "twirl.at", "twit.ac", "twit.la", "twurl.nl", "u.bb",
    "u.ikscp.com", "u.nu", "u.to", "u6e.de", "ub0.cc", "ucam.me", "ucr.li", "ug.to",
    "un.ly", "v.gd", "valv.es", "vaza.me", "vbly.com", "viralurl.com", "vox.com",
    "waa.ai", "wapo.st", "wbs.im", "wepr.ovh", "www.yourls.org", "x.co", "x.pr", "xm.si",
    "xs.ax", "y.ahoo.it", "yfrog.com", "yhoo.it", "zip.net", "zpr.io", "zy.ly",
    "discord.gift", "discordapp.com/gift", "steamcommunity.com",
    "free-nitro", "nitro-gift", "discord-nitro", "steam-gift"
]

# 3. ПОЛИТИЧЕСКИЕ И РЕЛИГИОЗНЫЕ ТЕМЫ
BUILTIN_POLITICS_WORDS = [
    "путин", "навальный", "зеленский", "коммунизм", "капитализм",
    "социализм", "ислам", "христианство", "буддизм", "религия",
    "политика", "нацизм", "фашизм", "расизм", "ксенофобия",
    "гомофобия", "трансфобия", "секта", "церковь", "идеология",
    "коммунист", "капиталист", "социалист", "анархист", "монархист",
    "либерал", "консерватор", "националист", "патриот", "космополит"
]

# 4. NSFW И ВЗРОСЛЫЙ КОНТЕНТ
BUILTIN_NSFW_WORDS = [
    "порно", "порн", "секс", "эротика", "фетиш", "фетишизм", "голый", "обнажённый",
    "инцест", "педофилия", "педофил", "зоофилия", "зоофил", "некрофилия", "некрофил",
    "содомия", "извращение", "извращенец", "разврат", "развратный", "пошлость",
    "пошлый", "непристойность", "непристойный", "вульгарный", "клубника",
    "взрослый", "18+", "nsfw", "porn", "xxx", "adult", "hentai", "ecchi", "yuri", "yaoi"
]

# 5. ЖЕСТОКОСТЬ И НАСИЛИЕ
BUILTIN_VIOLENCE_WORDS = [
    "насилие", "насиловать", "изнасилование", "жестокость", "жестокий", "садизм",
    "садист", "мазохизм", "мазохист", "самоубийство", "суицид", "суицидальный",
    "смерть", "убить", "убийство", "убийца", "убивать", "киллер", "маньяк",
    "зоофилия", "зоофил", "педофилия", "педофил", "некрофилия", "некрофил",
    "кровь", "кровопролитие", "расчленёнка", "расчленение", "пытки", "пытать",
    "издевательство", "издеваться", "глумиться"
]

# 6. НЕЗАКОННАЯ ДЕЯТЕЛЬНОСТЬ
BUILTIN_ILLEGAL_WORDS = [
    "пират", "пиратство", "пиратка", "взлом", "взломать", "хак", "хаки", "хакинг",
    "фишинг", "фишеры", "вирус", "вирусы", "вредонос", "вредоносный", "троян",
    "читы", "чит", "кряк", "крякнутый", "кейген", "лицензия", "взломанная",
    "воровство", "кража", "скам", "мошенничество", "мошенник", "обман", "махинация",
    "финансовая пирамида", "лохотрон", "развод", "кидалово", "фрод"
]

# 7. ЛИЧНЫЕ ДАННЫЕ (шаблоны)
PHONE_PATTERN = re.compile(r'\b(?:\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# ---------------------- ЗАГРУЗКА ИЗ ФАЙЛОВ (если есть) ----------------------

def load_bad_words():
    if not os.path.exists(WORDS_FILE):
        return BUILTIN_BAD_WORDS
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

def load_scam_domains():
    if not os.path.exists(SCAM_DOMAINS_FILE):
        return BUILTIN_SCAM_DOMAINS
    with open(SCAM_DOMAINS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

def load_politics_words():
    if not os.path.exists(POLITICS_WORDS_FILE):
        return BUILTIN_POLITICS_WORDS
    with open(POLITICS_WORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

# ---------------------- НАСТРОЙКИ ФИЛЬТРОВ ----------------------
MAX_CAPS_PERCENT = 70
MAX_REPEAT_CHARS = 10
MAX_REPEAT_WORDS = 5
MAX_MENTIONS = 5
MAX_EMOJIS = 10
MAX_ZALGO_CHARS = 3
MESSAGE_SPAM_LIMIT = 5
SPAM_WINDOW = 5

# ---------------------- ОСНОВНОЙ КОГ ----------------------
class AutoMod(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.bad_words = load_bad_words()
        self.scam_domains = load_scam_domains()
        self.politics_words = load_politics_words()
        self.user_messages = defaultdict(list)
        self.allowlist_domains = [
            "youtube.com", "youtu.be", "discord.com", "discord.gg",
            "github.com", "gitlab.com", "stackoverflow.com",
            "wikipedia.org", "ru.wikipedia.org", "google.com"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        # ===== ИГНОРИРУЕМ УКАЗАННЫЕ КАНАЛЫ =====
        if message.channel.id in IGNORED_CHANNEL_IDS:
            return
        for name in IGNORED_CHANNEL_NAMES:
            if name in message.channel.name.lower():
                return

        content = message.content
        if not content:
            return

        violation = None
        rule_name = None
        rule_number = None
        lowered = content.lower()

        # ---------- 1. ПОЛИТИКА, РЕЛИГИЯ, ИДЕОЛОГИИ (1.4) ----------
        for word in self.politics_words:
            if word in lowered:
                violation = f"Запрещённая тема: {word}"
                rule_name = "📜 Правило 1.4: Политика, религия и идеологии запрещены"
                rule_number = "1.4"
                break

        # ---------- 2. NSFW (2.1) ----------
        if not violation:
            for word in BUILTIN_NSFW_WORDS:
                if word in lowered:
                    violation = f"NSFW контент: {word}"
                    rule_name = "📜 Правило 2.1: Сервер полностью SFW"
                    rule_number = "2.1"
                    break

        # ---------- 3. СПАМ И ФЛУД (2.2) ----------
        if not violation:
            # Повтор символов
            for i in range(len(content) - MAX_REPEAT_CHARS):
                seq = content[i:i+MAX_REPEAT_CHARS+1]
                if len(set(seq)) == 1:
                    violation = f"Повтор символа '{seq[0]}' более {MAX_REPEAT_CHARS} раз"
                    rule_name = "📜 Правило 2.2: Спам, флуд и оффтоп запрещены"
                    rule_number = "2.2"
                    break
            # Повтор слов
            if not violation:
                words = content.split()
                for i in range(len(words) - MAX_REPEAT_WORDS + 1):
                    if len(set(words[i:i+MAX_REPEAT_WORDS])) == 1:
                        violation = f"Повтор слова '{words[i]}' более {MAX_REPEAT_WORDS} раз"
                        rule_name = "📜 Правило 2.2: Спам, флуд и оффтоп запрещены"
                        rule_number = "2.2"
                        break
            # Частые сообщения (спам по времени)
            if not violation:
                now = time.time()
                self.user_messages[message.author.id].append(now)
                self.user_messages[message.author.id] = [
                    t for t in self.user_messages[message.author.id] if now - t < SPAM_WINDOW
                ]
                if len(self.user_messages[message.author.id]) > MESSAGE_SPAM_LIMIT:
                    violation = f"Спам ({len(self.user_messages[message.author.id])} сообщений за {SPAM_WINDOW} сек)"
                    rule_name = "📜 Правило 2.2: Спам, флуд и оффтоп запрещены"
                    rule_number = "2.2"

        # ---------- 4. ЛИЧНЫЕ ДАННЫЕ (2.4) ----------
        if not violation:
            if PHONE_PATTERN.search(content) or EMAIL_PATTERN.search(content):
                violation = "Распространение личных данных"
                rule_name = "📜 Правило 2.4: Запрещено распространять личные данные других людей"
                rule_number = "2.4"

        # ---------- 5. РЕКЛАМА (2.5) ----------
        if not violation:
            ad_pattern = re.compile(r'(реклама|промо|сайт|канал|сервер|discord\.gg|discord\.com/invite)', re.IGNORECASE)
            if ad_pattern.search(content) and len(content) < 100:
                violation = "Реклама или само-промо"
                rule_name = "📜 Правило 2.5: Реклама и само-промо запрещены без разрешения"
                rule_number = "2.5"

        # ---------- 6. НЕЗАКОННАЯ ДЕЯТЕЛЬНОСТЬ (4.1) ----------
        if not violation:
            for word in BUILTIN_ILLEGAL_WORDS:
                if word in lowered:
                    violation = f"Обсуждение незаконной деятельности: {word}"
                    rule_name = "📜 Правило 4.1: Запрещена любая незаконная деятельность"
                    rule_number = "4.1"
                    break

        # ---------- 7. ССЫЛКИ (4.4) ----------
        if not violation:
            url_pattern = re.compile(r'https?://\S+')
            if url_pattern.search(content):
                is_allowed = False
                for domain in self.allowlist_domains:
                    if domain in lowered:
                        is_allowed = True
                        break
                if not is_allowed:
                    # Проверяем на сокращённые домены
                    for domain in self.scam_domains:
                        if domain in lowered:
                            violation = f"Сокращённая или подозрительная ссылка: {domain}"
                            rule_name = "📜 Правило 4.4: Сокращённые ссылки и фишинг запрещены"
                            rule_number = "4.4"
                            break
                    else:
                        # Любая ссылка, не в белом списке, считается нарушением
                        violation = "Использование ссылки без разрешения"
                        rule_name = "📜 Правило 4.4: Ссылки разрешены только с разрешения администрации"
                        rule_number = "4.4"

        # ---------- 8. ОСКОРБЛЕНИЯ (1.1) ----------
        if not violation:
            for word in self.bad_words:
                if word in lowered:
                    violation = f"Оскорбление: {word}"
                    rule_name = "📜 Правило 1.1: Относись с уважением к каждому"
                    rule_number = "1.1"
                    break

        # ---------- 9. ДИСКРИМИНАЦИЯ (1.10) ----------
        if not violation:
            discrimination_words = ["фашист", "расист", "нацист", "гомофоб", "ксенофоб", 
                                   "черножоп", "жид", "хохол", "москаль", "чурка", "узкоглазый"]
            for word in discrimination_words:
                if word in lowered:
                    violation = f"Дискриминационное высказывание: {word}"
                    rule_name = "📜 Правило 1.10: Запрещены проявления фашизма, расизма, ксенофобии и любой дискриминации"
                    rule_number = "1.10"
                    break

        # ---------- 10. ЖЕСТОКОСТЬ/НАСИЛИЕ (1.7) ----------
        if not violation:
            for word in BUILTIN_VIOLENCE_WORDS:
                if word in lowered:
                    violation = f"Романтизация жестокости/насилия: {word}"
                    rule_name = "📜 Правило 1.7: Запрещена романтизация жестокости, насилия, само-харма и зоофилии"
                    rule_number = "1.7"
                    break

        # ---------- 11. КАПС ----------
        if not violation and len(content) > 10:
            caps_count = sum(1 for c in content if c.isupper())
            caps_percent = caps_count / len(content) * 100
            if caps_percent > MAX_CAPS_PERCENT:
                violation = f"Капс ({caps_percent:.0f}% заглавных)"
                rule_name = "📜 Правило 1.1: Относись с уважением к каждому"
                rule_number = "1.1"

        # ---------- 12. ЭМОДЗИ ----------
        if not violation:
            emoji_pattern = re.compile(r'<a?:\w+:\d+>|[^\w\s]')
            emojis = emoji_pattern.findall(content)
            if len(emojis) > MAX_EMOJIS:
                violation = f"Слишком много эмодзи/смайликов ({len(emojis)})"
                rule_name = "📜 Правило 2.3: Контент публикуйте строго по тематике каналов"
                rule_number = "2.3"

        # ---------- 13. УПОМИНАНИЯ ----------
        if not violation and len(message.mentions) > MAX_MENTIONS:
            violation = f"Массовое упоминание ({len(message.mentions)} упоминаний)"
            rule_name = "📜 Правило 2.2: Спам, флуд и оффтоп запрещены"
            rule_number = "2.2"

        # ---------- 14. ZALGO ----------
        if not violation:
            zalgo_pattern = re.compile(r'[\u0300-\u036f\u0488-\u0489]')
            zalgo_chars = zalgo_pattern.findall(content)
            if len(zalgo_chars) > MAX_ZALGO_CHARS:
                violation = f"Чрезмерное использование Zalgo-символов ({len(zalgo_chars)})"
                rule_name = "📜 Правило 2.3: Не используйте странные символы"
                rule_number = "2.3"

        # ---------- 15. ПИНГ АДМИНИСТРАЦИИ (6.3) ----------
        if not violation:
            admin_roles = ['Хвостик порядка', 'Старший хвостик', 'Младшая лапка', 'Старшая лапка', 'Главная лапка']
            for role in message.role_mentions:
                if role.name in admin_roles:
                    violation = f"Пинг администрации (@{role.name}) без причины"
                    rule_name = "📜 Правило 6.3: Не пингуйте администрацию без веской причины"
                    rule_number = "6.3"
                    break

        # ---------- ВЫНОСИМ ВАРН ----------
        if violation:
            try:
                await message.delete()
            except:
                pass

            await message.channel.send(
                f"{message.author.mention} ⚠️ **Нарушение правил!**\n"
                f"📋 **{rule_name}**\n"
                f"❌ {violation}\n"
                f"🔔 Вам выдано предупреждение. Администрация рассмотрит наказание.",
                delete_after=10
            )

            warns_cog = self.bot.get_cog("Warns")
            if warns_cog:
                await warns_cog.send_warn_to_mod_channel(
                    user_id=message.author.id,
                    reason=f"{rule_number} - {violation}",
                    rule_name=rule_name,
                    message_link=message.jump_url
                )

def setup(bot: commands.InteractionBot):
    bot.add_cog(AutoMod(bot))