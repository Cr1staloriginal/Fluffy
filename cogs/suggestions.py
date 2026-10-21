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

async def init_tables():
    """Создаёт таблицы suggestions и suggestion_votes, если их нет."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_votes (
                suggestion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                vote TEXT NOT NULL,
                PRIMARY KEY (suggestion_id, user_id)
            )
        """)
        await db.commit()

async def get_votes(suggestion_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT vote, COUNT(*) FROM suggestion_votes WHERE suggestion_id = ? GROUP BY vote", (suggestion_id,)) as cur:
            rows = await cur.fetchall()
            up = 0
            down = 0
            for vote, count in rows:
                if vote == 'up':
                    up = count
                elif vote == 'down':
                    down = count
            return up, down

async def add_or_update_vote(suggestion_id: int, user_id: int, vote: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            INSERT OR REPLACE INTO suggestion_votes (suggestion_id, user_id, vote)
            VALUES (?, ?, ?)
        """, (suggestion_id, user_id, vote))
        await db.commit()

async def get_author_name(author_id: int, bot):
    user = await bot.get_user(author_id)
    return user.display_name if user else f"User {author_id}"

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
        await init_tables()
        text = inter.text_values.get("suggestion_text", "").strip()
        if not text:
            await inter.response.send_message("❌ Текст не может быть пустым.", ephemeral=True)
            return

        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute("INSERT INTO suggestions (author_id, text) VALUES (?, ?)", (inter.author.id, text))
            await db.commit()
            suggestion_id = cursor.lastrowid

        embed = disnake.Embed(
            title=f"⭐ Идея №{suggestion_id}",
            description=text,
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.add_field(name="👍", value="0", inline=True)
        embed.add_field(name="👎", value="0", inline=True)
        embed.set_footer(text="Голосуйте кнопками ниже")
        view = SuggestionView(suggestion_id, inter.author.id)
        await inter.response.send_message(embed=embed, view=view)

class SuggestionView(disnake.ui.View):
    def __init__(self, suggestion_id: int, author_id: int):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id
        self.author_id = author_id

    async def update_message(self, inter: disnake.MessageInteraction):
        up, down = await get_votes(self.suggestion_id)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT text, author_id FROM suggestions WHERE id = ?", (self.suggestion_id,)) as cur:
                row = await cur.fetchone()
                text = row[0] if row else ""
                author_id = row[1] if row else None
        embed = disnake.Embed(
            title=f"⭐ Идея №{self.suggestion_id}",
            description=text,
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        if author_id:
            user = inter.bot.get_user(author_id)
            embed.set_author(name=user.display_name if user else f"User {author_id}", icon_url=user.display_avatar.url if user else None)
        embed.add_field(name="👍", value=str(up), inline=True)
        embed.add_field(name="👎", value=str(down), inline=True)
        embed.set_footer(text="Голосуйте кнопками ниже")
        await inter.message.edit(embed=embed, view=self)

    @disnake.ui.button(label="👍", style=disnake.ButtonStyle.success)
    async def upvote_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await add_or_update_vote(self.suggestion_id, inter.author.id, 'up')
        await self.update_message(inter)
        await inter.response.send_message("✅ Ваш голос учтён!", ephemeral=True)

    @disnake.ui.button(label="👎", style=disnake.ButtonStyle.danger)
    async def downvote_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await add_or_update_vote(self.suggestion_id, inter.author.id, 'down')
        await self.update_message(inter)
        await inter.response.send_message("✅ Ваш голос учтён!", ephemeral=True)

    @disnake.ui.button(label="🔧 Принять решение", style=disnake.ButtonStyle.primary)
    async def resolve_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await inter.response.send_message("❌ Только персонал может принимать решения.", ephemeral=True)
            return
        await inter.response.send_message(
            "Выберите действие:",
            view=ActionSelectView(self.suggestion_id, inter),
            ephemeral=True
        )

class ActionSelectView(disnake.ui.View):
    def __init__(self, suggestion_id: int, original_inter: disnake.MessageInteraction):
        super().__init__(timeout=60)
        self.suggestion_id = suggestion_id
        self.original_inter = original_inter

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success)
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.resolve_suggestion(inter, "accepted", "✅ Принято!", disnake.Color.green())

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger)
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.resolve_suggestion(inter, "rejected", "❌ Отклонено", disnake.Color.red())

    async def resolve_suggestion(self, inter: disnake.MessageInteraction, status: str, status_text: str, color):
        await inter.response.defer()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT author_id, text FROM suggestions WHERE id = ?", (self.suggestion_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    await inter.followup.send("❌ Идея не найдена.", ephemeral=True)
                    return
                author_id, text = row
            await db.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, self.suggestion_id))
            await db.commit()
        up, down = await get_votes(self.suggestion_id)
        # Получаем имя автора
        user = inter.bot.get_user(author_id)
        author_name = user.display_name if user else f"User {author_id}"
        # Удаляем исходное сообщение (то, где были кнопки)
        try:
            await self.original_inter.message.delete()
        except:
            pass
        # Создаём новое сообщение с итогом
        embed = disnake.Embed(
            title=f"⭐ Идея №{self.suggestion_id} — {status_text}",
            description=text,
            color=color,
            timestamp=disnake.utils.utcnow()
        )
        embed.add_field(name="Автор", value=f"{author_name} (<@{author_id}>)", inline=False)
        embed.add_field(name="👍 Поддержало", value=str(up), inline=True)
        embed.add_field(name="👎 Против", value=str(down), inline=True)
        embed.set_footer(text=f"Решение принял: {inter.author.display_name}")
        await inter.channel.send(embed=embed)
        await inter.followup.send(f"✅ Идея #{self.suggestion_id} {status_text.lower()}", ephemeral=True)
        self.stop()

class Suggestions(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="идея", description="📝 Предложить идею для сервера")
    async def idea(self, inter: disnake.ApplicationCommandInteraction):
        await init_tables()
        await inter.response.send_modal(SuggestionModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Suggestions(bot))