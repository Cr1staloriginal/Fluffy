import io
import logging

import disnake
from disnake.ext import commands

from database import log_event
from utils.colors import main_color
from utils.ticket_metadata import build_ticket_topic, parse_ticket_topic
from utils.ticket_permissions import get_staff_roles, is_staff_member

logger = logging.getLogger(__name__)


def render_ticket_transcript(messages, max_chars: int = 1_500_000) -> str:
    """Render fetched Discord messages into a bounded plain-text transcript."""
    lines = []
    current_size = 0
    for message in messages:
        author = getattr(message, "author", None)
        author_name = getattr(author, "display_name", None) or str(author or "Неизвестный автор")
        created_at = getattr(message, "created_at", None)
        timestamp = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or "время неизвестно")
        content = (getattr(message, "content", None) or "").strip() or "[без текстового содержимого]"
        block = [f"[{timestamp}] {author_name} (ID: {getattr(author, 'id', '—')}):", content]
        attachments = getattr(message, "attachments", ()) or ()
        for attachment in attachments:
            block.append(f"  Вложение: {getattr(attachment, 'filename', 'файл')} — {getattr(attachment, 'url', '')}")
        embeds = getattr(message, "embeds", None) or ()
        if embeds:
            block.append(f"  Встроенных объектов: {len(embeds)}")
        block.append("")
        block_text = "\n".join(block)
        if current_size + len(block_text) > max_chars:
            lines.append("[Транскрипт сокращён: достигнут лимит размера]")
            break
        lines.append(block_text)
        current_size += len(block_text)
    return "\n".join(lines) or "В тикете пока нет сообщений."


TICKET_CATEGORY = "Тикеты"
CLOSED_CATEGORY_NAME = "Закрытые тикеты"

TICKET_CATEGORIES = (
    "Общий вопрос",
    "Техническая проблема",
    "Жалоба",
    "Партнёрство",
)


class TicketModal(disnake.ui.Modal):
    def __init__(self, category: str):
        self.category = category
        components = [
            disnake.ui.TextInput(
                label="Причина обращения",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Опишите проблему или вопрос...",
                custom_id="ticket_reason",
                required=True,
                max_length=1000,
            )
        ]
        super().__init__(title=f"Тикет: {category}"[:45], components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        reason = interaction.text_values.get("ticket_reason", "Не указана").strip()
        guild = interaction.guild
        author = interaction.author

        if guild is None or author is None:
            await interaction.edit_original_response(content="❌ Не удалось определить сервер или автора обращения.")
            return

        # Prevent duplicate open tickets while allowing a new request after closure.
        for existing in guild.text_channels:
            metadata = parse_ticket_topic(existing.topic)
            if (
                metadata.get("creator") == str(author.id)
                and existing.category is not None
                and existing.category.name != CLOSED_CATEGORY_NAME
            ):
                await interaction.edit_original_response(content=f"У тебя уже есть открытый тикет: {existing.mention}")
                return

        bot_member = guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_channels:
            await interaction.edit_original_response(content="❌ У бота нет права `manage_channels`.")
            return

        category_channel = disnake.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category_channel is None:
            try:
                category_channel = await guild.create_category(
                    TICKET_CATEGORY,
                    reason="Создание категории тикетов Fluffy",
                )
            except disnake.HTTPException:
                logger.exception("Не удалось создать категорию тикетов в guild=%s", guild.id)
                await interaction.edit_original_response(content="❌ Не удалось создать категорию тикетов. Проверьте права бота.")
                return

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            author: disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            bot_member: disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }
        for role in get_staff_roles(guild):
            overwrites[role] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

        owner = guild.owner
        if owner is not None:
            overwrites[owner] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )

        topic = build_ticket_topic(author.id, self.category)
        channel_name = f"ticket-{author.id}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category_channel,
                topic=topic,
                overwrites=overwrites,
                reason=f"Тикет от {author} ({author.id})",
            )
        except disnake.HTTPException:
            logger.exception("Не удалось создать канал тикета в guild=%s для user=%s", guild.id, author.id)
            await interaction.edit_original_response(content="❌ Не удалось создать канал тикета. Проверьте права и лимиты Discord.")
            return

        welcome_embed = disnake.Embed(
            title="📩 Ваш тикет создан",
            description=(
                f"**Категория:** {self.category}\n"
                f"**Причина:** {reason or 'Не указана'}\n\n"
                "Опишите проблему подробнее. Персонал скоро свяжется с вами."
            ),
            color=main_color(),
        )
        welcome_embed.add_field(name="Ответственный", value="Не назначен", inline=True)
        try:
            await channel.send(
                content=author.mention,
                embed=welcome_embed,
                view=CloseTicketButton(channel.id, author.id),
                allowed_mentions=disnake.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except disnake.HTTPException:
            logger.exception("Не удалось отправить стартовое сообщение тикета channel=%s", channel.id)
            await interaction.edit_original_response(content=f"⚠️ Канал создан: {channel.mention}, но стартовое сообщение отправить не удалось.")
            return

        await interaction.edit_original_response(content=f"✅ Тикет создан: {channel.mention}")

        log_embed = disnake.Embed(
            title="🎫 Создан тикет",
            color=main_color(),
            timestamp=disnake.utils.utcnow(),
        )
        log_embed.add_field(name="Пользователь", value=f"{author} ({author.id})", inline=False)
        log_embed.add_field(name="Категория", value=self.category, inline=True)
        log_embed.add_field(name="Канал", value=channel.mention, inline=False)
        log_embed.add_field(name="Причина", value=reason[:1000] or "Не указана", inline=False)
        dispatcher = getattr(interaction.bot, "log_dispatcher", None)
        if dispatcher:
            await dispatcher.send("tickets", log_embed)
        await log_event("ticket_open", f"{author.id}|{channel.id}|{self.category}|{reason}")


class TicketCategoryView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @disnake.ui.string_select(
        placeholder="Выберите категорию обращения",
        min_values=1,
        max_values=1,
        options=[disnake.SelectOption(label=category, value=category) for category in TICKET_CATEGORIES],
        custom_id="fluffy:ticket:category",
    )
    async def select_category(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.send_modal(TicketModal(select.values[0]))


class CloseTicketButton(disnake.ui.View):
    def __init__(self, channel_id: int = 0, creator_id: int = 0):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.creator_id = creator_id

    @disnake.ui.button(
        label="🙋 Взять тикет",
        style=disnake.ButtonStyle.success,
        custom_id="fluffy:ticket:claim",
    )
    async def claim_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        member = inter.author
        if not is_staff_member(member):
            await inter.response.send_message("❌ Взять тикет может только администрация или модерация.", ephemeral=True)
            return
        if inter.guild is None or not isinstance(inter.channel, disnake.TextChannel):
            await inter.response.send_message("❌ Действие доступно только в канале тикета.", ephemeral=True)
            return

        metadata = parse_ticket_topic(inter.channel.topic)
        if not metadata:
            # Keep tickets created before this update manageable as well.
            metadata = {
                "creator": str(self.creator_id or 0),
                "category": "Общий вопрос",
                "claimed_by": "",
            }

        current_claim = metadata.get("claimed_by", "")
        if current_claim and current_claim != str(member.id):
            await inter.response.send_message(f"Тикет уже взял <@{current_claim}>.", ephemeral=True)
            return

        new_claim = "" if current_claim == str(member.id) else str(member.id)
        try:
            await inter.channel.edit(
                topic=build_ticket_topic(
                    int(metadata["creator"]),
                    metadata.get("category", "Общий вопрос"),
                    new_claim,
                ),
                reason=f"Изменение ответственного тикета: {member} ({member.id})",
            )
        except (KeyError, ValueError, disnake.HTTPException):
            logger.exception("Не удалось обновить ответственного тикета channel=%s", inter.channel.id)
            await inter.response.send_message("❌ Не удалось изменить ответственного. Проверьте права бота.", ephemeral=True)
            return

        if new_claim:
            await inter.response.send_message("✅ Ты назначен ответственным за этот тикет.", ephemeral=True)
            await inter.channel.send(f"🙋 {member.mention} взял обращение в работу.")
            await log_event("ticket_claim", f"{inter.channel.id}|{member.id}")
        else:
            await inter.response.send_message("✅ Ты снял с себя ответственность за тикет.", ephemeral=True)
            await inter.channel.send(f"↩️ {member.mention} снял с себя ответственность.")
            await log_event("ticket_unclaim", f"{inter.channel.id}|{member.id}")

    @disnake.ui.button(
        label="🔒 Закрыть тикет",
        style=disnake.ButtonStyle.danger,
        custom_id="close_ticket",
    )
    async def close_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.channel_id and inter.channel.id != self.channel_id:
            await inter.response.send_message("❌ Эта кнопка работает только в этом канале.", ephemeral=True)
            return

        member = inter.author
        if not is_staff_member(member):
            await inter.response.send_message("❌ Закрыть тикет может только администрация или модерация.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        if guild is None:
            await inter.followup.send("❌ Не удалось определить сервер.", ephemeral=True)
            return

        metadata = parse_ticket_topic(getattr(inter.channel, "topic", None))
        creator_id = int(metadata["creator"]) if metadata.get("creator", "").isdigit() else self.creator_id

        closed_category = disnake.utils.get(guild.categories, name=CLOSED_CATEGORY_NAME)
        if closed_category is None:
            try:
                closed_category = await guild.create_category(
                    CLOSED_CATEGORY_NAME,
                    reason="Создание архива закрытых тикетов",
                )
            except disnake.HTTPException:
                logger.exception("Не удалось создать категорию закрытых тикетов guild=%s", guild.id)
                await inter.followup.send("❌ Не удалось создать категорию архива. Проверьте права бота.", ephemeral=True)
                return

        bot_member = guild.me
        new_overwrites = {guild.default_role: disnake.PermissionOverwrite(view_channel=False)}
        for role in get_staff_roles(guild):
            new_overwrites[role] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )

        owner = guild.owner
        if owner is not None:
            new_overwrites[owner] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )
        if bot_member is not None:
            new_overwrites[bot_member] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            )

        creator = guild.get_member(creator_id) if creator_id else None
        if creator is not None:
            new_overwrites[creator] = disnake.PermissionOverwrite(
                view_channel=False,
                send_messages=False,
                read_message_history=False,
            )

        try:
            await inter.channel.edit(
                category=closed_category,
                overwrites=new_overwrites,
                reason=f"Тикет закрыт модератором {member} ({member.id})",
            )
        except disnake.HTTPException:
            logger.exception("Не удалось архивировать тикет channel=%s", inter.channel.id)
            await inter.followup.send("❌ Не удалось переместить тикет в архив. Проверьте права бота.", ephemeral=True)
            return

        await inter.channel.send("🔒 Тикет закрыт и перемещён в архив. Доступ сохранён у администрации и модерации.")
        await inter.followup.send("✅ Тикет закрыт. Он перемещён в архив.", ephemeral=True)

        open_category = disnake.utils.get(guild.categories, name=TICKET_CATEGORY)
        if open_category:
            open_tickets = [
                channel for channel in open_category.text_channels
                if channel.name.startswith("ticket-")
            ]
            if not open_tickets:
                try:
                    await open_category.delete(reason="Категория открытых тикетов пуста")
                except disnake.HTTPException:
                    logger.warning("Не удалось удалить пустую категорию тикетов guild=%s", guild.id, exc_info=True)

        log_embed = disnake.Embed(
            title="🔒 Закрыт тикет",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow(),
        )
        log_embed.add_field(name="Канал", value=f"#{inter.channel.name} (архив)", inline=False)
        log_embed.add_field(name="Закрыл", value=f"{member} ({member.id})", inline=False)
        dispatcher = getattr(inter.bot, "log_dispatcher", None)
        if dispatcher:
            await dispatcher.send("tickets", log_embed)
        await log_event("ticket_close", f"{inter.channel.id}|closed by {member.id}|creator {creator_id}")


class CreateTicketView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="🎫 Создать тикет", style=disnake.ButtonStyle.primary, custom_id="create_ticket")
    async def create_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message(
            "Выбери категорию обращения:",
            view=TicketCategoryView(),
            ephemeral=True,
        )


class Tickets(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    def cog_load(self):
        self.bot.add_view(CreateTicketView())
        self.bot.add_view(CloseTicketButton())

    @commands.slash_command(
        name="ticket_transcript",
        description="📄 Выгрузить переписку текущего тикета в TXT",
    )
    async def ticket_transcript(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None or not isinstance(inter.channel, disnake.TextChannel):
            await inter.response.send_message("❌ Команда доступна только внутри тикета на сервере.", ephemeral=True)
            return
        if not is_staff_member(inter.author):
            await inter.response.send_message("❌ Выгружать транскрипты может только администрация или модерация.", ephemeral=True)
            return
        metadata = parse_ticket_topic(inter.channel.topic)
        if not metadata and not inter.channel.name.startswith("ticket-"):
            await inter.response.send_message("❌ Эта команда работает только в канале тикета.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        try:
            messages = [message async for message in inter.channel.history(limit=1000, oldest_first=False)]\n            messages.reverse()
            transcript = render_ticket_transcript(messages)
            file = disnake.File(
                fp=io.BytesIO(transcript.encode("utf-8")),
                filename=f"ticket-{inter.channel.id}-transcript.txt",
            )
            await inter.edit_original_response(
                content=f"📄 Транскрипт тикета **#{inter.channel.name}** готов.",
                file=file,
            )
        except (disnake.Forbidden, disnake.HTTPException, OSError):
            logger.exception("Не удалось сформировать транскрипт тикета channel=%s", inter.channel.id)
            await inter.edit_original_response(content="❌ Не удалось выгрузить транскрипт. Проверьте доступ бота к истории канала.")

    @commands.slash_command(
        name="setup_tickets",
        description="Отправить панель создания тикетов в текущий канал",
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="🎫 Центр обращений",
            description=(
                "Создай тикет, выбери категорию и опиши вопрос.\n"
                "Персонал сможет взять обращение в работу и закрыть его после решения."
            ),
            color=main_color(),
        )
        await inter.response.send_message(embed=embed, view=CreateTicketView())


def setup(bot: commands.InteractionBot):
    bot.add_cog(Tickets(bot))
