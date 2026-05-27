import disnake
from disnake.ext import commands
import asyncio
from typing import Optional
import os

MUTED_ROLE_NAME = "🔇Замьючен"
OWNER_ID = int(os.getenv("OWNER_ID", 0))

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, inter: disnake.ApplicationCommandInteraction) -> bool:
        if not isinstance(inter.author, disnake.Member):
            return False
        return inter.author.guild_permissions.manage_messages or inter.author.id == OWNER_ID

    @commands.slash_command(name="kick", description="Выгнать участника")
    @commands.has_permissions(kick_members=True)
    async def kick(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: Optional[str] = "Не указана"):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Только на сервере.", ephemeral=True)
            return
        if member.top_role >= guild.me.top_role:
            await inter.response.send_message("🚫 Роль выше моей.", ephemeral=True)
            return
        if member == inter.author:
            await inter.response.send_message("🚫 Нельзя кикнуть себя.", ephemeral=True)
            return
        await member.kick(reason=reason)
        await inter.response.send_message(f"👢 {member} кикнут. Причина: {reason}")
        embed = disnake.Embed(title="🔨 Кик", color=disnake.Color.red(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

    @commands.slash_command(name="ban", description="Забанить участника")
    @commands.has_permissions(ban_members=True)
    async def ban(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: Optional[str] = "Не указана"):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Только на сервере.", ephemeral=True)
            return
        if member.top_role >= guild.me.top_role:
            await inter.response.send_message("🚫 Роль выше моей.", ephemeral=True)
            return
        await member.ban(reason=reason)
        await inter.response.send_message(f"🔨 {member} забанен. Причина: {reason}")
        embed = disnake.Embed(title="🔨 Бан", color=disnake.Color.dark_red(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

    @commands.slash_command(name="mute", description="Выдать мьют участнику")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, minutes: int = 10, reason: Optional[str] = None):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Только на сервере.", ephemeral=True)
            return
        role = disnake.utils.get(guild.roles, name=MUTED_ROLE_NAME)
        if role is None:
            role = await guild.create_role(name=MUTED_ROLE_NAME)
            for channel in guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        await member.add_roles(role, reason=reason)
        await inter.response.send_message(f"🔇 {member} замучен на {minutes} мин.")
        embed = disnake.Embed(title="🔇 Мут", color=disnake.Color.orange(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Длительность", value=f"{minutes} мин.", inline=False)
        embed.add_field(name="Причина", value=reason or "Не указана", inline=False)
        await self.bot.log_dispatcher.send("mod", embed)
        await asyncio.sleep(minutes * 60)
        if role in member.roles:
            await member.remove_roles(role)
            await inter.followup.send(f"🔊 {member} размучен.", ephemeral=True)

    @commands.slash_command(name="purge", description="Удалить сообщения (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, inter: disnake.ApplicationCommandInteraction, amount: int = 10):
        if not (1 <= amount <= 100):
            await inter.response.send_message("❌ От 1 до 100.", ephemeral=True)
            return
        await inter.response.defer()
        deleted = await inter.channel.purge(limit=amount + 1)
        await inter.edit_original_response(content=f"🧹 Удалено {len(deleted) - 1} сообщений.")
        embed = disnake.Embed(title="🧹 Очистка чата", color=disnake.Color.purple(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Канал", value=inter.channel.mention, inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Удалено", value=str(len(deleted) - 1), inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

def setup(bot):
    bot.add_cog(Moderation(bot))