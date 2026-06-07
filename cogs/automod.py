import disnake
from disnake.ext import commands
import os

WORDS_FILE = os.path.join(os.path.dirname(__file__), "..", "words.txt")

def load_bad_words():
    if not os.path.exists(WORDS_FILE):
        return []
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

MAX_CAPS_PERCENT = 70
MAX_REPEAT_CHARS = 10
MAX_MENTIONS = 5

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.bad_words = load_bad_words()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        content = message.content
        if not content:
            return

        # Проверки по очереди
        violation = None
        rule_name = None

        # 1. Капс
        if len(content) > 10:
            caps_count = sum(1 for c in content if c.isupper())
            caps_percent = caps_count / len(content) * 100
            if caps_percent > MAX_CAPS_PERCENT:
                violation = f"Использование капса ({caps_percent:.0f}% заглавных)"
                rule_name = "Правило 3.1: Не злоупотребляйте заглавными буквами"

        # 2. Повторяющиеся символы
        if not violation:
            for i in range(len(content) - MAX_REPEAT_CHARS):
                seq = content[i:i+MAX_REPEAT_CHARS+1]
                if len(set(seq)) == 1:
                    violation = f"Повтор символа '{seq[0]}' более {MAX_REPEAT_CHARS} раз подряд"
                    rule_name = "Правило 3.2: Не спамьте повторяющимися символами"
                    break

        # 3. Много упоминаний
        if not violation and len(message.mentions) > MAX_MENTIONS:
            violation = f"Массовое упоминание участников ({len(message.mentions)} упоминаний)"
            rule_name = "Правило 3.3: Не упоминайте много людей без причины"

        # 4. Запрещённые слова
        if not violation:
            lowered = content.lower()
            for word in self.bad_words:
                if word in lowered:
                    violation = f"Использование запрещённого слова: {word}"
                    rule_name = "Правило 2.1: Запрещена нецензурная лексика"
                    break

        if violation:
            try:
                await message.delete()
            except:
                pass

            # Уведомление пользователю
            await message.channel.send(
                f"{message.author.mention} ⚠️ **Нарушение правил!**\n"
                f"📋 **{rule_name}**\n"
                f"❌ {violation}\n"
                f"🔔 Вам выдано предупреждение. Администрация рассмотрит наказание.",
                delete_after=10
            )

            # Отправляем варн в канал модерации
            warns_cog = self.bot.get_cog("Warns")
            if warns_cog:
                await warns_cog.send_warn_to_mod_channel(
                    user_id=message.author.id,
                    reason=violation,
                    rule_name=rule_name,
                    message_link=message.jump_url
                )

def setup(bot):
    bot.add_cog(AutoMod(bot))