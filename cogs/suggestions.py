import disnake
from disnake.ext import commands
from database import (
    add_suggestion, get_suggestion, add_vote,
    get_suggestion_votes_by_type, close_suggestion
)
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
                label="Текст предложения",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Опишите ваше предложение...",
                custom_id="suggestion_text",
                required=True,
                max_length=1500
            )
        ]
        super().__init__(title="📝 Новое предложение", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        text = inter.text_values.get("suggestion_text", "").strip()
        if not text:
            await inter.response.send_message("❌ Текст предложения не может быть пустым.", ephemeral=True)
            return
        suggestion_id = await add_suggestion(inter.author.id, text)
        embed = disnake.Embed(
            title=f"📌 Предложение №{suggestion_id}",
            description=text,
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.add_field(name="👥 Оценка персонала", value="⏳ нет голосов", inline=True)
        embed.add_field(name="👤 Оценка участников", value="⏳ нет голосов", inline=True)
        embed.add_field(name="🔢 Общий рейтинг", value="⏳ нет голосов", inline=True)
        embed.set_footer(text="Нажмите на кнопку ниже, чтобы оценить предложение")
        view = SuggestionView(suggestion_id, inter.author.id)
        await inter.response.send_message(embed=embed, view=view)

class RatingModal(disnake.ui.Modal):
    def __init__(self, suggestion_id: int):
        self.suggestion_id = suggestion_id
        components = [
            disnake.ui.TextInput(
                label="Ваша оценка от 1 до 5",
                style=disnake.TextInputStyle.short,
                placeholder="1 — очень плохо, 5 — отлично",
                custom_id="rating",
                required=True,
                max_length=1
            )
        ]
        super().__init__(title="⭐ Оценить предложение", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        rating_str = inter.text_values.get("rating", "").strip()
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                raise ValueError
        except:
            await inter.response.send_message("❌ Оценка должна быть числом от 1 до 5.", ephemeral=True)
            return
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        vote_type = "staff" if is_staff else "member"
        await add_vote(self.suggestion_id, inter.author.id, vote_type, rating)
        await update_suggestion_embed(inter, self.suggestion_id)
        await inter.response.send_message("✅ Ваша оценка учтена!", ephemeral=True)

class SuggestionView(disnake.ui.View):
    def __init__(self, suggestion_id: int, author_id: int):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id
        self.author_id = author_id

    @disnake.ui.button(label="⭐ Оценить", style=disnake.ButtonStyle.primary)
    async def rate_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(RatingModal(self.suggestion_id))

    @disnake.ui.button(label="🔧 Принять решение", style=disnake.ButtonStyle.secondary)
    async def resolve_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await inter.response.send_message("❌ Только персонал может управлять предложениями.", ephemeral=True)
            return
        await inter.response.send_message(
            "Выберите действие:",
            view=ActionSelectView(self.suggestion_id),
            ephemeral=True
        )

class ActionSelectView(disnake.ui.View):
    def __init__(self, suggestion_id: int):
        super().__init__(timeout=60)
        self.suggestion_id = suggestion_id

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success)
    async def accept_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await close_suggestion(self.suggestion_id, "accepted")
        await inter.response.send_message("✅ Предложение принято! Статус обновлён.", ephemeral=True)
        await update_suggestion_embed(inter, self.suggestion_id, closed=True)
        self.stop()

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger)
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await close_suggestion(self.suggestion_id, "rejected")
        await inter.response.send_message("❌ Предложение отклонено.", ephemeral=True)
        await update_suggestion_embed(inter, self.suggestion_id, closed=True)
        self.stop()

    @disnake.ui.button(label="⏳ В работу", style=disnake.ButtonStyle.primary)
    async def work_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await close_suggestion(self.suggestion_id, "in_work")
        await inter.response.send_message("🛠️ Предложение принято в работу!", ephemeral=True)
        await update_suggestion_embed(inter, self.suggestion_id, closed=True)
        self.stop()

async def update_suggestion_embed(inter: disnake.MessageInteraction, suggestion_id: int, closed: bool = False):
    from database import get_suggestion, get_suggestion_votes_by_type
    suggestion = await get_suggestion(suggestion_id)
    if not suggestion:
        return
    staff_avg, staff_count = await get_suggestion_votes_by_type(suggestion_id, "staff")
    member_avg, member_count = await get_suggestion_votes_by_type(suggestion_id, "member")
    all_ratings = []
    if staff_avg:
        all_ratings.extend([staff_avg] * staff_count)
    if member_avg:
        all_ratings.extend([member_avg] * member_count)
    total_avg = sum(all_ratings) / len(all_ratings) if all_ratings else None

    staff_text = f"{staff_avg:.2f} 🟢 ({staff_count} голосов)" if staff_avg else "⏳ нет голосов"
    member_text = f"{member_avg:.2f} 🟢 ({member_count} голосов)" if member_avg else "⏳ нет голосов"
    total_text = f"{total_avg:.2f} 🟢" if total_avg else "⏳ нет голосов"

    status_map = {
        "open": "🟡 На рассмотрении",
        "accepted": "✅ Принято",
        "rejected": "❌ Отклонено",
        "in_work": "🛠️ В работе"
    }
    status = status_map.get(suggestion[4], "🟡 На рассмотрении")
    embed = disnake.Embed(
        title=f"📌 Предложение №{suggestion_id}",
        description=suggestion[2],
        color=main_color() if suggestion[4] == "open" else disnake.Color.dark_grey(),
        timestamp=disnake.utils.utcnow()
    )
    embed.set_author(name=f"Автор: <@{suggestion[1]}>", icon_url=None)
    embed.add_field(name="👥 Оценка персонала", value=staff_text, inline=True)
    embed.add_field(name="👤 Оценка участников", value=member_text, inline=True)
    embed.add_field(name="🔢 Общий рейтинг", value=total_text, inline=True)
    embed.add_field(name="📋 Статус", value=status, inline=False)
    if closed:
        embed.set_footer(text="Предложение закрыто")
    try:
        await inter.edit_original_response(embed=embed, view=None if closed else SuggestionView(suggestion_id, suggestion[1]))
    except:
        pass

class Suggestions(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="предложение", description="📝 Создать новое предложение")
    async def suggestion(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(SuggestionModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Suggestions(bot))