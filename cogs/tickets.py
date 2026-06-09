import disnake
from disnake.ext import commands
import asyncio
from database import log_event

TICKET_CATEGORY = 'Тикеты'
STAFF_ROLE_NAMES = ['🦊 Хвостик порядка', '🦊 Старший хвостик', '🐾 Младшая лапка', '🐾 Старшая лапка', '🐾 Главная лапка']

class Tickets(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="ticket", description="🎫 Создать тикет")
    async def ticket(self, inter: disnake.ApplicationCommandInteraction, reason: str = None):
        guild = inter.guild
        if not guild:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return

        category = disnake.utils.get(guild.categories, name=TICKET_CATEGORY)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            inter.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_name in STAFF_ROLE_NAMES:
            role = disnake.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)

        ch = await guild.create_text_channel(f"ticket-{inter.author.name}", category=category, overwrites=overwrites)
        await ch.send(f"📩 Тикет от {inter.author.mention}\n📝 Причина: {reason or 'Не указана'}")
        await inter.response.send_message(f"✅ Тикет создан: {ch.mention}", ephemeral=True)

        embed = disnake.Embed(title="🎫 Создан тикет", color=disnake.Color.green(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Пользователь", value=f"{inter.author} ({inter.author.id})", inline=False)
        embed.add_field(name="Канал", value=ch.mention, inline=False)
        embed.add_field(name="Причина", value=reason or "Не указана", inline=False)
        await self.bot.log_dispatcher.send("tickets", embed)
        await log_event('ticket_open', f'{inter.author.id}|{ch.id}')

    @commands.slash_command(
        name="close_ticket",
        description="🔒 Закрыть текущий тикет",
        default_member_permissions=disnake.Permissions.manage_channels  # БЕЗ .value
    )
    @commands.has_permissions(manage_channels=True)
    async def close_ticket(self, inter: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel = None):
        ch = channel or inter.channel
        if not ch.name.startswith("ticket-"):
            await inter.response.send_message("❌ Эта команда работает только в тикет-каналах.", ephemeral=True)
            return

        await inter.response.send_message("⏳ Тикет будет удалён через 10 секунд...", ephemeral=True)
        await ch.send("🔒 Тикет закрывается. Спасибо за обращение!")

        embed = disnake.Embed(title="🔒 Закрыт тикет", color=disnake.Color.red(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Канал", value=ch.mention, inline=False)
        embed.add_field(name="Закрыл", value=inter.author.mention, inline=False)
        await self.bot.log_dispatcher.send("tickets", embed)

        await asyncio.sleep(10)
        await ch.delete()
        await log_event('ticket_close', f'{ch.id}')

def setup(bot: commands.InteractionBot):
    bot.add_cog(Tickets(bot))