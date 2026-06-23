import disnake
from disnake.ext import commands
import asyncio
import os
from database import log_event
from utils.colors import main_color

TICKET_CATEGORY = "Тикеты"
CLOSED_CATEGORY_NAME = "Закрытые тикеты"
STAFF_ROLE_NAMES = [
    "🦊 Хвостик порядка",
    "🦊 Старший хвостик",
    "🐾 Младшая лапка",
    "🐾 Старшая лапка",
    "🐾 Главная лапка"
]
MOD_LOG_CHANNEL_ID = int(os.getenv("LOG_CH_TICKETS", 0))

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
        await interaction.response.defer()
        reason = interaction.text_values.get("ticket_reason", "Не указана")
        guild = interaction.guild
        author = interaction.user

        if not guild.me.guild_permissions.manage_channels:
            await interaction.edit_original_response(content="❌ У бота нет права `manage_channels`.")
            return

        category = disnake.utils.get(guild.categories, name=TICKET_CATEGORY)
        if not category:
            try:
                category = await guild.create_category(TICKET_CATEGORY)
                print(f"[Tickets] Создана категория {TICKET_CATEGORY}")
            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Ошибка создания категории: {e}")
                return

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            author: disnake.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        }
        for role_name in STAFF_ROLE_NAMES:
            role = disnake.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{author.name}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Тикет от {author}"
            )
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Ошибка создания канала: {e}")
            return

        welcome_embed = disnake.Embed(
            title="📩 Ваш тикет создан",
            description=f"**Причина:** {reason}\n\nОпишите проблему подробнее. Персонал скоро свяжется с вами.",
            color=main_color()
        )
        close_view = CloseTicketButton(channel.id, author.id)
        await channel.send(content=author.mention, embed=welcome_embed, view=close_view)

        confirm_msg = await interaction.edit_original_response(content=f"✅ Тикет создан: {channel.mention}")
        await asyncio.sleep(7)
        try:
            await confirm_msg.delete()
        except:
            pass

        log_embed = disnake.Embed(
            title="🎫 Создан тикет",
            color=main_color(),
            timestamp=disnake.utils.utcnow()
        )
        log_embed.add_field(name="Пользователь", value=f"{author} ({author.id})", inline=False)
        log_embed.add_field(name="Канал", value=channel.mention, inline=False)
        log_embed.add_field(name="Причина", value=reason, inline=False)
        if MOD_LOG_CHANNEL_ID:
            log_channel = interaction.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=log_embed)
        await log_event("ticket_open", f"{author.id}|{channel.id}|{reason}")

class CloseTicketButton(disnake.ui.View):
    def __init__(self, channel_id: int, creator_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.creator_id = creator_id

    @disnake.ui.button(label="🔒 Закрыть тикет", style=disnake.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.channel.id != self.channel_id:
            await inter.response.send_message("❌ Эта кнопка работает только в этом канале.", ephemeral=True)
            return
        await inter.response.defer()
        member = inter.author
        is_staff = any(role.name in STAFF_ROLE_NAMES for role in member.roles) or member.guild_permissions.administrator
        if not is_staff:
            await inter.followup.send("❌ Только персонал может закрыть тикет.", ephemeral=True)
            return

        guild = inter.guild
        closed_category = disnake.utils.get(guild.categories, name=CLOSED_CATEGORY_NAME)
        if not closed_category:
            try:
                closed_category = await guild.create_category(CLOSED_CATEGORY_NAME)
                print(f"[Tickets] Создана категория {CLOSED_CATEGORY_NAME}")
            except Exception as e:
                await inter.followup.send(f"❌ Не удалось создать категорию для закрытых тикетов: {e}")
                return

        new_overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
        }
        for role_name in STAFF_ROLE_NAMES:
            role = disnake.utils.get(guild.roles, name=role_name)
            if role:
                new_overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=False)

        creator = guild.get_member(self.creator_id)
        if creator and not any(role.name in STAFF_ROLE_NAMES for role in creator.roles):
            new_overwrites[creator] = disnake.PermissionOverwrite(read_messages=False)

        try:
            await inter.channel.edit(category=closed_category, overwrites=new_overwrites)
        except Exception as e:
            await inter.followup.send(f"❌ Ошибка перемещения канала: {e}")
            return

        await inter.channel.send("🔒 Тикет закрыт и перемещён в архив. Доступ к каналу имеют только сотрудники.")
        await inter.followup.send("✅ Тикет закрыт. Он перемещён в архив и скрыт от участника.")

        open_category = disnake.utils.get(guild.categories, name=TICKET_CATEGORY)
        if open_category:
            open_tickets = [ch for ch in open_category.text_channels if ch.name.startswith("ticket-")]
            if not open_tickets:
                try:
                    await open_category.delete()
                    print(f"[Tickets] Категория {TICKET_CATEGORY} удалена (пуста).")
                except Exception as e:
                    print(f"[Tickets] Ошибка удаления категории {TICKET_CATEGORY}: {e}")

        log_embed = disnake.Embed(
            title="🔒 Закрыт тикет",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        log_embed.add_field(name="Канал", value=f"#{inter.channel.name} (перемещён в архив, скрыт)", inline=False)
        log_embed.add_field(name="Закрыл", value=member.mention, inline=False)
        if MOD_LOG_CHANNEL_ID:
            log_channel = inter.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=log_embed)
        await log_event("ticket_close", f"{inter.channel.id}|closed by {member.id}|creator {self.creator_id}")

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
            title="🎫 Создать тикет",
            description="Создайте тикет и опишите в нём свою проблему",
            color=main_color()
        )
        view = CreateTicketView()
        await inter.response.send_message(embed=embed, view=view)

def setup(bot: commands.InteractionBot):
    bot.add_cog(Tickets(bot))