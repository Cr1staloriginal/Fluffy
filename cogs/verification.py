import disnake
from disnake.ext import commands
import os
import datetime
import aiosqlite
from database import DB_PATH, log_event
from utils.colors import main_color, accent_color
from utils.ticket_permissions import is_staff_member

# Переменные из .env
SUBMIT_CHANNEL_ID = int(os.getenv("VERIFY_SUBMIT_CHANNEL_ID", 0))
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID", 0))
REJECTED_ROLE_ID = int(os.getenv("REJECTED_ROLE_ID", 0))
MODERATION_ROLE_ID = int(os.getenv("MODERATION_ROLE_ID", 0))  # Новая переменная для пинга
GUILD_ID = int(os.getenv("GUILD_ID", 0))

STAFF_ROLE_NAMES = [
    "⛑️Верификатор",
]


def is_submission_cooldown_active(submitted_at, now=None, cooldown_seconds: int = 60) -> bool:
    """Check the pending-application cooldown; malformed timestamps fail open."""
    if not submitted_at or cooldown_seconds <= 0:
        return False
    try:
        submitted = (
            submitted_at
            if isinstance(submitted_at, datetime.datetime)
            else datetime.datetime.fromisoformat(str(submitted_at).replace("Z", "+00:00"))
        )
        if submitted.tzinfo is None:
            current = now or datetime.datetime.utcnow()
        else:
            current = now or datetime.datetime.now(datetime.timezone.utc)
            if current.tzinfo is None:
                current = current.replace(tzinfo=datetime.timezone.utc)
        elapsed = (current - submitted).total_seconds()
        return 0 <= elapsed < cooldown_seconds
    except (TypeError, ValueError, OverflowError):
        return False


def verification_cooldown_seconds() -> int:
    try:
        return max(10, min(int(os.getenv("VERIFY_SUBMISSION_COOLDOWN_SECONDS", "60")), 3600))
    except (TypeError, ValueError):
        return 60

async def init_verification_table():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verification_applications (
                user_id INTEGER PRIMARY KEY,
                message_id INTEGER,
                channel_id INTEGER,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        await db.commit()

async def save_application(user_id: int, message_id: int, channel_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            INSERT OR REPLACE INTO verification_applications (user_id, message_id, channel_id, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, message_id, channel_id))
        await db.commit()

async def get_application(user_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT message_id, channel_id, status, submitted_at FROM verification_applications WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

async def delete_application(user_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM verification_applications WHERE user_id = ?", (user_id,))
        await db.commit()

async def update_application_status(user_id: int, status: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE verification_applications SET status = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

class VerificationModal(disnake.ui.Modal):
    def __init__(self):
        questions = [
            "Как вы узнали о нашем сервере?",
            'Что для вас лично означает "фурри-фэндом"?',
            "Вас начнут оскорблять в чате, ваши действия?",
            "Есть ли у вас фурсона? Если есть расскажи:",
            "Ознакомились ли вы с правилами сервера?"
        ]
        components = [
            disnake.ui.TextInput(
                label=q[:45],
                style=disnake.TextInputStyle.paragraph if i > 1 else disnake.TextInputStyle.short,
                placeholder=f"Ответ на вопрос {i+1}...",
                custom_id=f"q{i}",
                required=True,
                max_length=1000
            ) for i, q in enumerate(questions)
        ]
        super().__init__(title="📝 Заявка на вступление", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        await init_verification_table()

        # Если есть старая заявка, удаляем её
        existing = await get_application(interaction.author.id)
        if existing:
            old_msg_id, old_channel_id, status, submitted_at = existing
            cooldown = verification_cooldown_seconds()
            if status == "pending" and is_submission_cooldown_active(submitted_at, cooldown_seconds=cooldown):
                await interaction.edit_original_response(
                    content=f"⏳ Заявка уже отправлена. Повторная отправка будет доступна примерно через {cooldown} секунд."
                )
                return
            if status == "pending":
                old_channel = interaction.bot.get_channel(old_channel_id)
                if old_channel:
                    try:
                        old_msg = await old_channel.fetch_message(old_msg_id)
                        await old_msg.delete()
                    except:
                        pass
            await delete_application(interaction.author.id)

        answers = [interaction.text_values.get(f"q{i}", "Нет ответа") for i in range(5)]
        channel = interaction.bot.get_channel(SUBMIT_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Канал для заявок не настроен. Сообщите администрации.", ephemeral=True)
            return

        embed = disnake.Embed(
            title="📩 Новая заявка на вступление",
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_author(name=interaction.author.display_name, icon_url=interaction.author.display_avatar.url)
        embed.set_thumbnail(url=interaction.author.display_avatar.url)

        questions = [
            "1. Как вы узнали о нашем сервере?",
            "2. Что для вас лично означает 'фурри-фэндом'?",
            "3. Вас начнут оскорблять в чате, ваши действия?",
            "4. Есть ли у вас фурсона? Если есть расскажи:",
            "5. Ознакомились ли вы с правилами сервера?"
        ]
        for q, a in zip(questions, answers):
            embed.add_field(name=q, value=a[:1024] or "—", inline=False)

        embed.set_footer(text=f"ID пользователя: {interaction.author.id}")

        view = VerificationActions(interaction.author.id, interaction.author.display_name)

        # Отправляем сообщение с упоминанием роли модерации
        content = f"<@&{MODERATION_ROLE_ID}>" if MODERATION_ROLE_ID else ""
        msg = await channel.send(content=content, embed=embed, view=view)

        # Сохраняем ID сообщения
        await save_application(interaction.author.id, msg.id, channel.id)

        await interaction.response.send_message("✅ Ваша заявка отправлена на рассмотрение. Ожидайте ответа модераторов.", ephemeral=True)
        await log_event("verification_submit", f"{interaction.author.id} submitted application")

class VerificationActions(disnake.ui.View):
    def __init__(self, user_id: int, user_name: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("❌ Действие доступно только на сервере.", ephemeral=True)
            return False
        member = interaction.author
        if not isinstance(member, disnake.Member) or not (
            is_staff_member(member) or any(role.name in STAFF_ROLE_NAMES for role in member.roles)
        ):
            await interaction.response.send_message("❌ Обрабатывать заявки может только администрация или модерация.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success, custom_id="fluffy:verification:accept")
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        if not member:
            await interaction.followup.send("❌ Пользователь не найден на сервере.", ephemeral=True)
            return

        role = guild.get_role(VERIFIED_ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Заявка одобрена")
                await interaction.followup.send(f"✅ Пользователю {member.mention} выдана роль {role.mention}.", ephemeral=False)
                try:
                    await member.send(f"🎉 Ваша заявка на сервер **{guild.name}** была одобрена! Добро пожаловать!")
                except:
                    pass
                await update_application_status(self.user_id, "accepted")
                await log_event("verification_accept", f"{self.user_id} accepted by {interaction.user.id}")
                await interaction.message.delete()
                await delete_application(self.user_id)
            except Exception as e:
                await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Роль для верифицированных не найдена.", ephemeral=True)

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger, custom_id="fluffy:verification:reject")
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        if not member:
            await interaction.followup.send("❌ Пользователь не найден на сервере.", ephemeral=True)
            return

        role = guild.get_role(REJECTED_ROLE_ID) if REJECTED_ROLE_ID else None
        if role:
            try:
                await member.add_roles(role, reason="Заявка отклонена")
                await interaction.followup.send(f"❌ Пользователю {member.mention} выдана роль {role.mention} (отказ).", ephemeral=False)
            except:
                await interaction.followup.send(f"❌ Не удалось выдать роль отказа.", ephemeral=True)
        else:
            ver_role = guild.get_role(VERIFIED_ROLE_ID)
            if ver_role and ver_role in member.roles:
                try:
                    await member.remove_roles(ver_role, reason="Заявка отклонена")
                except:
                    pass
            await interaction.followup.send(f"❌ Заявка пользователя {member.mention} отклонена.", ephemeral=False)

        try:
            await member.send(f"❌ Ваша заявка на сервер **{guild.name}** была отклонена. Вы можете подать новую заявку повторно.")
        except:
            pass

        await update_application_status(self.user_id, "rejected")
        await log_event("verification_reject", f"{self.user_id} rejected by {interaction.user.id}")
        await interaction.message.delete()
        await delete_application(self.user_id)

class Verification(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def cog_load(self):
        """Restore persistent moderation buttons for pending applications after restart."""
        await init_verification_table()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT user_id, message_id FROM verification_applications WHERE status='pending'"
            ) as cur:
                pending = await cur.fetchall()
        for user_id, message_id in pending:
            self.bot.add_view(VerificationActions(user_id, str(user_id)), message_id=message_id)

    @commands.slash_command(
        name="setup_verification",
        description="📋 Отправить embed с кнопкой для подачи заявки в текущий канал",
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    @commands.has_permissions(administrator=True)
    async def setup_verification(self, inter: disnake.ApplicationCommandInteraction):
        await init_verification_table()
        embed = disnake.Embed(
            title="📝 Подача заявки на вступление",
            description=(
                "Чтобы присоединиться к нашему серверу, заполните анкету.\n"
                "Нажмите на кнопку ниже и ответьте на вопросы.\n"
                "Модерация рассмотрит вашу заявку в ближайшее время."
            ),
            color=main_color()
        )
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(
            label="📩 Подать заявку",
            style=disnake.ButtonStyle.primary,
            custom_id="open_verification_modal"
        ))
        await inter.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: disnake.Interaction):
        # Application-command and modal interactions do not expose a message component.
        component = getattr(interaction, "component", None)
        if component and component.custom_id == "open_verification_modal":
            await interaction.response.send_modal(VerificationModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Verification(bot))