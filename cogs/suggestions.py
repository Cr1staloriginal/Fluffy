import disnake
from disnake.ext import commands
import aiosqlite
import os
from database import DB_PATH
from utils.colors import main_color

STAFF_ROLE_NAMES = [
    "🦊 Хвостик порядка",
    "🦊 Старший хвостик",
    "🐾 Младшая лапка",
    "🐾 Старшая лапка",
    "🐾 Главная лапка"
]

class SuggestionModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Текст идеи",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Опишите вашу идею...",
                custom_id="suggestion_text",
                required=True,
                max_length=1000
            )
        ]
        super().__init__(title="📝 Новая идея", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        text = inter.text_values.get("suggestion_text", "").strip()
        if not text:
            await inter.response.send_message("❌ Текст не может быть пустым.", ephemeral=True)
            return

        # Сохраняем в БД
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute("INSERT INTO suggestions (author_id, text) VALUES (?, ?)", (inter.author.id, text))
            await db.commit()
            suggestion_id = cursor.lastrowid

        embed = disnake.Embed(
            title=f"✨ Идея №{suggestion_id}",
            description=text,
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.set_footer(text="Нажмите на кнопку, чтобы принять или отклонить")
        view = SuggestionView(suggestion_id, inter.author.id)

        await inter.response.send_message(embed=embed, view=view)

class SuggestionView(disnake.ui.View):
    def __init__(self, suggestion_id: int, author_id: int):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id
        self.author_id = author_id

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success)
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.resolve_suggestion(inter, "accepted", "✅ Принято!")

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger)
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.resolve_suggestion(inter, "rejected", "❌ Отклонено")

    async def resolve_suggestion(self, inter: disnake.MessageInteraction, status: str, status_text: str):
        # Проверка прав: только персонал или автор?
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await inter.response.send_message("❌ Только персонал может принимать решения.", ephemeral=True)
            return

        # Получаем данные из БД
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT author_id, text FROM suggestions WHERE id = ?", (self.suggestion_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    await inter.response.send_message("❌ Идея не найдена.", ephemeral=True)
                    return
                author_id, text = row
            await db.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, self.suggestion_id))
            await db.commit()

        # Удаляем исходное сообщение с кнопками
        await inter.message.delete()

        # Создаём новое сообщение с результатом
        embed = disnake.Embed(
            title=f"✨ Идея №{self.suggestion_id} — {status_text}",
            description=text,
            color=disnake.Color.green() if status == "accepted" else disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_author(name=f"Автор: <@{author_id}>")
        embed.set_footer(text=f"Решение принял: {member.display_name}")

        await inter.channel.send(embed=embed)
        await inter.response.send_message(f"✅ Идея #{self.suggestion_id} {status_text.lower()}", ephemeral=True)

class Suggestions(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="идея", description="📝 Предложить идею для сервера")
    async def idea(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(SuggestionModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Suggestions(bot))