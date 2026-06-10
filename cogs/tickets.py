import disnake
from disnake.ext import commands
import asyncio
import os
from database import log_event

# --- Конфигурация (измените под свой сервер) ---
TICKET_CATEGORY_NAME = "Тикеты"            # Название категории (будет создана)
STAFF_ROLE_NAMES = [
    "🦊 Хвостик порядка",
    "🦊 Старший хвостик",
    "🐾 Младшая лапка",
    "🐾 Старшая лапка",
    "🐾 Главная лапка"
]
MOD_LOG_CHANNEL_ID = int(os.getenv("LOG_CH_MOD", 0))  # ID канала для логов (из .env)

# -------------------------------------------------

class TicketModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Причина обращения",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Опишите проблему или вопрос...",
                custom_id="ticket_reason",
                required=True,
                max_length=1000
            )
        ]
        super().__init__(title="Создание тикета", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        # Немедленно подтверждаем получение, чтобы не было тайм-аута
        await interaction.response.defer()
        reason = interaction.text_values.get("ticket_reason", "Не указана")
        guild = interaction.guild
        author = interaction.user

        # 1. Проверка прав бота
        if not guild.me.guild_permissions.manage_channels:
            await interaction.edit_original_response(
                content="❌ У бота нет права `manage_channels`. Выдайте ему это право и попробуйте снова."
            )
            return

        # 2. Поиск или создание категории
        category = disnake.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            try:
                category = await guild.create_category(TICKET_CATEGORY_NAME)
                print(f"[Tickets] Создана категория {TICKET_CATEGORY_NAME}")
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"❌ Не удалось создать категорию: {e}"
                )
                return

        # 3. Настройка прав доступа
        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),  # скрыть от всех
            author: disnake.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, embed_links=True
            )
        }
        for role_name in STAFF_ROLE_NAMES:
            role = disnake.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = disnake.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )
        # Дополнительно даём доступ администраторам (если не вошли в список)
        admin_role = disnake.utils.get(guild.roles, name="Administrator")
        if admin_role and admin_role not in overwrites:
            overwrites[admin_role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)

        # 4. Создание канала внутри категории
        channel_name = f"ticket-{author.name}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Тикет от {author}"
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Ошибка создания канала: {e}"
            )
            return

        # 5. Приветственное сообщение с кнопкой "Закрыть тикет"
        embed = disnake.Embed(
            title="📩 Ваш тикет создан",
            description=f"**Причина:** {reason}\n\nОпишите вашу проблему подробнее. Персонал скоро свяжется с вами.",
            color=disnake.Color.blurple()
        )
        view = CloseTicketButton(channel.id)
        await channel.send(content=author.mention, embed=embed, view=view)

        # 6. Удаляем исходное сообщение с кнопкой "Создать тикет" (если оно существует)
        if interaction.message:
            try:
                await interaction.message.delete()
            except:
                pass

        # 7. Логируем создание в канал модерации
        log_embed = disnake.Embed(
            title="🎫 Создан тикет",
            color=disnake.Color.green(),
            timestamp=disnake.utils.utcnow()
        )
        log_embed.add_field(name="Пользователь", value=f"{author} ({author.id})", inline=False)
        log_embed.add_field(name="Канал", value=channel.mention, inline=False)
        log_embed.add_field(name="Причина", value=reason, inline=False)

        if MOD_LOG_CHANNEL_ID:
            log_channel = interaction.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=log_embed)

        # 8. Финальное подтверждение пользователю
        await interaction.edit_original_response(
            content=f"✅ Тикет создан: {channel.mention}"
        )
        await log_event("ticket_open", f"{author.id}|{channel.id}|{reason}")


class CloseTicketButton(disnake.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @disnake.ui.button(label="🔒 Закрыть тикет", style=disnake.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Проверка, что кнопка нажата в том же канале
        if inter.channel.id != self.channel_id:
            await inter.response.send_message(
                "❌ Эта кнопка работает только в соответствующем тикет-канале.",
                ephemeral=True
            )
            return

        await inter.response.defer()

        # Проверка прав: закрыть может только персонал или администратор
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await inter.followup.send("❌ Только персонал может закрыть тикет.", ephemeral=True)
            return

        # Уведомления о закрытии
        await inter.followup.send("⏳ Тикет будет удалён через 10 секунд...")
        await inter.channel.send("🔒 Тикет закрывается. Спасибо за обращение!")

        # Логируем закрытие в канал модерации
        log_embed = disnake.Embed(
            title="🔒 Закрыт тикет",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        log_embed.add_field(name="Канал", value=inter.channel.mention, inline=False)
        log_embed.add_field(name="Закрыл", value=member.mention, inline=False)
        if MOD_LOG_CHANNEL_ID:
            log_channel = inter.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=log_embed)

        await asyncio.sleep(10)

        # Удаляем канал
        try:
            await inter.channel.delete()
            await log_event("ticket_close", f"{inter.channel.id}|closed by {member.id}")
        except Exception as e:
            await inter.followup.send(f"❌ Не удалось удалить канал: {e}")


class CreateTicketView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="🎫 Создать тикет", style=disnake.ButtonStyle.primary, custom_id="create_ticket")
    async def create_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(TicketModal())


class Tickets(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(
        name="setup_tickets",
        description="Отправить embed с кнопкой для создания тикетов в текущий канал"
    )
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="🎫 Система тикетов",
            description="Нажмите на кнопку ниже, чтобы создать тикет. Укажите причину обращения, и мы свяжемся с вами.",
            color=disnake.Color.blurple()
        )
        view = CreateTicketView()
        await inter.response.send_message(embed=embed, view=view)


def setup(bot: commands.InteractionBot):
    bot.add_cog(Tickets(bot))