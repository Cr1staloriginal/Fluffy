import disnake
from disnake.ext import commands
from database import log_event

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        embed = disnake.Embed(
            title="📥 Присоединился",
            description=f"{member.mention} ({member.id})",
            color=disnake.Color.green(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_footer(text=f"Всего участников: {member.guild.member_count}")
        await self.bot.log_dispatcher.send("members", embed)
        await log_event("member_join", str(member.id))

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        embed = disnake.Embed(
            title="📤 Покинул",
            description=f"{member.name}#{member.discriminator} ({member.id})",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        await self.bot.log_dispatcher.send("members", embed)
        await log_event("member_remove", str(member.id))

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        # Логи изменения ролей
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            embed = disnake.Embed(
                title="🔄 Изменены роли",
                color=disnake.Color.gold(),
                timestamp=disnake.utils.utcnow()
            )
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            if added:
                embed.add_field(name="Добавлены", value=", ".join(r.mention for r in added), inline=False)
            if removed:
                embed.add_field(name="Удалены", value=", ".join(r.mention for r in removed), inline=False)
            embed.set_footer(text="Discord не передаёт, кто изменил роли")
            await self.bot.log_dispatcher.send("members", embed)
            await log_event("member_update_roles", f"{after.id}|added={[r.id for r in added]}|removed={[r.id for r in removed]}")

        # Логи изменения ника
        if before.display_name != after.display_name:
            embed = disnake.Embed(
                title="✏️ Изменён ник",
                color=disnake.Color.blue(),
                timestamp=disnake.utils.utcnow()
            )
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            embed.add_field(name="Было", value=before.display_name, inline=False)
            embed.add_field(name="Стало", value=after.display_name, inline=False)
            await self.bot.log_dispatcher.send("members", embed)
            await log_event("member_update_nick", f"{after.id}|{before.display_name}->{after.display_name}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if message.author.bot:
            return
        embed = disnake.Embed(
            title="🗑 Удалено",
            description=f"**Автор:** {message.author.mention}\n**Канал:** {message.channel.mention}\n**Текст:**\n{message.content[:1000]}",
            color=disnake.Color.orange(),
            timestamp=disnake.utils.utcnow()
        )
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_delete", f"{message.author.id}|{message.content or ''}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if before.author.bot or before.content == after.content:
            return
        embed = disnake.Embed(
            title="✏ Изменено",
            description=f"**Автор:** {before.author.mention}\n**Канал:** {before.channel.mention}\n**Было:**\n{before.content[:500]}\n**Стало:**\n{after.content[:500]}",
            color=disnake.Color.blue(),
            timestamp=disnake.utils.utcnow()
        )
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_edit", f"{before.author.id}|{before.content or ''}->{after.content or ''}")

def setup(bot):
    bot.add_cog(Logs(bot))
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_edit", f"{before.author.id}|{before.content or ''}->{after.content or ''}")

def setup(bot):
    bot.add_cog(Logs(bot))
