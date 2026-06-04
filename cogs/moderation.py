import disnake
from disnake.ext import commands
import asyncio
from typing import Optional
import os

MUTED_ROLE_NAME = "🔇Замьючен"
OWNER_ID = int(os.getenv("OWNER_ID", 0))

class Moderation(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.active_mutes = {}  # Словарь для отслеживания активных мьютов

    @commands.slash_command(
        name="kick",
        description="Выгнать участника",
        default_member_permissions=disnake.Permissions.kick_members.value
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: Optional[str] = "Не указана"):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return
        if member.top_role >= guild.me.top_role:
            await inter.response.send_message("🚫 Роль пользователя выше или равна моей.", ephemeral=True)
            return
        if member == inter.author:
            await inter.response.send_message("🚫 Нельзя кикнуть себя.", ephemeral=True)
            return
        await member.kick(reason=reason)
        await inter.response.send_message(f"👢 {member.mention} был кикнут. Причина: {reason}")
        embed = disnake.Embed(title="🔨 Кик", color=disnake.Color.red(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

    @commands.slash_command(
        name="ban",
        description="Забанить участника",
        default_member_permissions=disnake.Permissions.ban_members.value
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, reason: Optional[str] = "Не указана"):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return
        if member.top_role >= guild.me.top_role:
            await inter.response.send_message("🚫 Роль пользователя выше или равна моей.", ephemeral=True)
            return
        if member == inter.author:
            await inter.response.send_message("🚫 Нельзя забанить себя.", ephemeral=True)
            return
        await member.ban(reason=reason)
        await inter.response.send_message(f"🔨 {member.mention} был забанен. Причина: {reason}")
        embed = disnake.Embed(title="🔨 Бан", color=disnake.Color.dark_red(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Причина", value=reason, inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

    @commands.slash_command(
        name="mute",
        description="Выдать мьют участнику",
        default_member_permissions=disnake.Permissions.manage_roles.value
    )
    @commands.has_permissions(manage_roles=True)
    async def mute(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, minutes: int = 10, reason: Optional[str] = None):
        guild = inter.guild
        if not guild or not guild.me:
            await inter.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return
        if member.top_role >= guild.me.top_role:
            await inter.response.send_message("🚫 Роль пользователя выше или равна моей.", ephemeral=True)
            return
        if member == inter.author:
            await inter.response.send_message("🚫 Нельзя замьютить себя.", ephemeral=True)
            return
        
        role = disnake.utils.get(guild.roles, name=MUTED_ROLE_NAME)
        if role is None:
            role = await guild.create_role(name=MUTED_ROLE_NAME)
            for channel in guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        
        await member.add_roles(role, reason=reason)
        await inter.response.send_message(f"🔇 {member.mention} замучен на {minutes} мин.")
        embed = disnake.Embed(title="🔇 Мут", color=disnake.Color.orange(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Длительность", value=f"{minutes} мин.", inline=False)
        embed.add_field(name="Причина", value=reason or "Не указана", inline=False)
        await self.bot.log_dispatcher.send("mod", embed)
        
        # Запускаем размут в фоновом режиме
        mute_key = f"{guild.id}_{member.id}"
        self.active_mutes[mute_key] = asyncio.create_task(
            self._unmute_after_delay(member, role, minutes, inter)
        )

    async def _unmute_after_delay(self, member: disnake.Member, role: disnake.Role, minutes: int, inter: disnake.ApplicationCommandInteraction):
        """Размучивает участника после истечения времени"""
        try:
            await asyncio.sleep(minutes * 60)
            if role in member.roles:
                await member.remove_roles(role)
                await inter.followup.send(f"🔊 {member.mention} размучен.")
        except Exception as e:
            print(f"Ошибка при размучивании: {e}")
        finally:
            mute_key = f"{member.guild.id}_{member.id}"
            self.active_mutes.pop(mute_key, None)

    @commands.slash_command(
        name="purge",
        description="Удалить сообщения (1-100)",
        default_member_permissions=disnake.Permissions.manage_messages.value
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, inter: disnake.ApplicationCommandInteraction, amount: int = 10):
        if not (1 <= amount <= 100):
            await inter.response.send_message("❌ От 1 до 100.", ephemeral=True)
            return
        await inter.response.defer()
        deleted = await inter.channel.purge(limit=amount)
        await inter.edit_original_response(content=f"🧹 Удалено {len(deleted)} сообщений.")
        embed = disnake.Embed(title="🧹 Очистка чата", color=disnake.Color.purple(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Канал", value=inter.channel.mention, inline=False)
        embed.add_field(name="Модератор", value=inter.author.mention, inline=False)
        embed.add_field(name="Удалено", value=str(len(deleted)), inline=False)
        await self.bot.log_dispatcher.send("mod", embed)

def setup(bot: commands.InteractionBot):
    bot.add_cog(Moderation(bot))
