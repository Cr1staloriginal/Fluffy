import disnake
from disnake.ext import commands
import os
import aiosqlite
from database import DB_PATH, log_event
from utils.colors import main_color, accent_color

# Переменные из .env
SUBMIT_CHANNEL_ID = int(os.getenv("VERIFY_SUBMIT_CHANNEL_ID", 0))
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID", 0))
REJECTED_ROLE_ID = int(os.getenv("REJECTED_ROLE_ID", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))

# Роли, которые могут принимать решения (модераторы)
STAFF_ROLE_NAMES = [
    "🦊 Хвостик порядка",
    "🦊 Старший хвостик",
    "🐾 Младшая лапка",
    "🐾 Старшая лапка",
    "🐾 Главная лапка"
]

async def init_verification_table():
    """Создаёт таблицу для отслеживания заявок, если её нет."""
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
        async with db.execute("SELECT message_id, channel_id, status FROM verification_applications WHERE user_id = ?", (user_id,)) as cur:
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

        # Проверяем, есть ли уже заявка у пользователя
        existing = await get_application(interaction.author.id)
        if existing:
            # Если заявка уже есть, удаляем старую
            old_msg_id, old_channel_id, status = existing
            if status == "pending":
                # Удаляем старую заявку из канала
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

        msg = await channel.send(embed=embed, view=view)
        await save_application(interaction.author.id, msg.id, channel.id)

        await interaction.response.send_message("✅ Ваша заявка отправлена на рассмотрение. Ожидайте ответа модераторов.", ephemeral=True)
        await log_event("verification_submit", f"{interaction.author.id} submitted application")

class VerificationActions(disnake.ui.View):
    def __init__(self, user_id: int, user_name: str):
        super().__init__(timeout=86400)
        self.user_id = user_id
        self.user_name = user_name

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("❌ Вы не найдены на сервере.", ephemeral=True)
            return False
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await interaction.response.send_message("❌ Только модерация может обрабатывать заявки.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Принять", style=disnake.ButtonStyle.success)
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

    @disnake.ui.button(label="❌ Отклонить", style=disnake.ButtonStyle.danger)
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
            # Если роли нет – просто убираем роль верификации, если есть
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

    @commands.slash_command(
        name="setup_verification",
        description="📋 Отправить embed с кнопкой для подачи заявки в текущий канал"
    )
    @commands.has_permissions(administrator=True)
    async def setup_verification(self, inter: disnake.ApplicationCommandInteraction):
        """Отправляет embed с кнопкой 'Подать заявку' в текущий канал."""
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
    async def on_interaction(self, interaction: disnake.MessageInteraction):
        if interaction.component.custom_id == "open_verification_modal":
            # Проверяем, не забанен ли пользователь (если есть роль "Отклонено" – разрешаем повторную подачу)
            await interaction.response.send_modal(VerificationModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Verification(bot))