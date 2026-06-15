import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from database import set_birthday, get_birthday, delete_birthday, get_today_birthdays
from utils.colors import main_color, accent_color

MOSCOW_TZ = timezone(timedelta(hours=3))

class SetBirthdayModal(disnake.ui.Modal):
    def __init__(self, action: str):
        self.action = action
        title = "Установить день рождения" if action == "set" else "Изменить день рождения"
        components = [
            disnake.ui.TextInput(
                label="Дата (ДД-ММ)",
                placeholder="Например: 15-08",
                custom_id="birthday_date",
                required=True,
                max_length=5
            )
        ]
        super().__init__(title=title, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        date_str = inter.text_values.get("birthday_date", "").strip()
        try:
            day, month = map(int, date_str.split('-'))
            if not (1 <= day <= 31 and 1 <= month <= 12):
                raise ValueError
        except:
            await inter.response.send_message(
                "❌ Неверный формат. Используйте ДД-ММ, например: 15-08",
                ephemeral=True
            )
            return
        await set_birthday(inter.author.id, f"{day:02d}-{month:02d}")
        await inter.response.send_message(
            f"✅ Твой день рождения ({day:02d}.{month:02d}) сохранён! Я поздравлю тебя в ЛС.",
            ephemeral=True
        )

class BirthdayView(disnake.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.user_id:
            await inter.response.send_message("❌ Эти кнопки не для вас.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="🎂 Сохранить дату", style=disnake.ButtonStyle.success, custom_id="bday_set")
    async def set_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(SetBirthdayModal(action="set"))

    @disnake.ui.button(label="✏️ Изменить дату", style=disnake.ButtonStyle.primary, custom_id="bday_edit")
    async def edit_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(SetBirthdayModal(action="edit"))

    @disnake.ui.button(label="🗑️ Удалить дату", style=disnake.ButtonStyle.danger, custom_id="bday_del")
    async def delete_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if await delete_birthday(inter.author.id):
            await inter.response.send_message("🗑️ Твой день рождения удалён из памяти бота.", ephemeral=True)
        else:
            await inter.response.send_message("❌ У тебя не было сохранённой даты.", ephemeral=True)

class Birthday(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.birthday_checker.start()

    def cog_unload(self):
        self.birthday_checker.cancel()

    @tasks.loop(time=datetime.time(hour=12, minute=0, tzinfo=MOSCOW_TZ))
    async def birthday_checker(self):
        now = datetime.now(MOSCOW_TZ)
        today_str = now.strftime("%d-%m")
        user_ids = await get_today_birthdays(today_str)
        for user_id in user_ids:
            user = self.bot.get_user(user_id)
            if user and not user.bot:
                try:
                    embed = disnake.Embed(
                        title="🎂 С днём рождения! 🎉",
                        description=(
                            f"**{user.display_name}**, поздравляем тебя!\n"
                            "Желаем счастья, здоровья, пушистых объятий и отличного настроения! 🐾\n"
                            "Пусть на сервере тебе будет всегда уютно и весело!"
                        ),
                        color=accent_color(),
                        timestamp=datetime.now(MOSCOW_TZ)
                    )
                    embed.set_thumbnail(url=user.display_avatar.url)
                    await user.send(embed=embed)
                except disnake.Forbidden:
                    print(f"[Birthday] Не удалось отправить ЛС пользователю {user_id} — ЛС закрыты.")
                except Exception as e:
                    print(f"[Birthday] Ошибка при отправке поздравления {user_id}: {e}")

    @birthday_checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()
        print("[Birthday] Задача проверки дней рождений запущена (каждый день в 12:00 МСК).")

    @commands.slash_command(name="др", description="🎂 Управление днём рождения (кнопки)")
    async def birthday(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="🎂 День рождения",
            description=(
                "Нажми на кнопку, чтобы сохранить, изменить или удалить дату твоего дня рождения.\n"
                "Я буду поздравлять тебя в личные сообщения в этот день."
            ),
            color=main_color()
        )
        view = BirthdayView(inter.author.id)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

def setup(bot: commands.InteractionBot):
    bot.add_cog(Birthday(bot))