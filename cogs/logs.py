import disnake
from disnake.ext import commands
from database import log_event

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DEBUG] Ког Logs загружен")

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        print(f"[DEBUG] on_member_join: {member}")
        embed = disnake.Embed(
            title="📥 Присоединился",
            description=f"{member.mention} ({member.id})",
            color=disnake.Color.green(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_footer(text=f"Всего участников: {member.guild.member_count}")
        try:
            await self.bot.log_dispatcher.send("members", embed)
        except Exception as e:
            print(f"Logs: не удалось отправить в log_dispatcher on_member_join: {e}")
        try:
            await log_event("member_join", str(member.id))
        except Exception as e:
            print(f"Logs: не удалось записать событие в БД on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        print(f"[DEBUG] on_member_remove: {member}")
        embed = disnake.Embed(
            title="📤 Покинул",
            description=f"{member.name} ({member.id})",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        try:
            await self.bot.log_dispatcher.send("members", embed)
        except Exception as e:
            print(f"Logs: не удалось отправить в log_dispatcher on_member_remove: {e}")
        try:
            await log_event("member_remove", str(member.id))
        except Exception as e:
            print(f"Logs: не удалось записать событие в БД on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        try:
            print(f"[DEBUG] on_member_update: {before.display_name} -> {after.display_name}")
        except Exception:
            print("[DEBUG] on_member_update: (некорректные display_name)")

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
            try:
                await self.bot.log_dispatcher.send("members", embed)
            except Exception as e:
                print(f"Logs: не удалось отправить в log_dispatcher on_member_update roles: {e}")
            try:
                await log_event("member_update_roles", f"{after.id}|added={[r.id for r in added]}|removed={[r.id for r in removed]}")
            except Exception as e:
                print(f"Logs: не удалось записать событие в БД on_member_update roles: {e}")

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
            try:
                await self.bot.log_dispatcher.send("members", embed)
            except Exception as e:
                print(f"Logs: не удалось отправить в log_dispatcher on_member_update nick: {e}")
            try:
                await log_event("member_update_nick", f"{after.id}|{before.display_name}->{after.display_name}")
            except Exception as e:
                print(f"Logs: не удалось записать событие в БД on_member_update nick: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        try:
            author = message.author
            preview = (message.content or "")[:20]
            print(f"[DEBUG] on_message_delete: {author} - {preview}")
        except Exception:
            print("[DEBUG] on_message_delete: неизвестное сообщение")
            return

        if message.author.bot:
            return
        embed = disnake.Embed(
            title="🗑 Удалено",
            description=f"**Автор:** {message.author.mention}\n**Канал:** {getattr(message.channel, 'mention', str(message.channel))}\n**Текст:**\n{(message.content or '')[:1000]}",
            color=disnake.Color.orange(),
            timestamp=disnake.utils.utcnow()
        )
        try:
            await self.bot.log_dispatcher.send("messages", embed)
        except Exception as e:
            print(f"Logs: не удалось отправить в log_dispatcher on_message_delete: {e}")
        try:
            await log_event("message_delete", f"{message.author.id}|{message.content or ''}")
        except Exception as e:
            print(f"Logs: не удалось записать событие в БД on_message_delete: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if before.author.bot or (before.content or "") == (after.content or ""):
            return
        try:
            print(f"[DEBUG] on_message_edit: {before.author}")
        except Exception:
            print("[DEBUG] on_message_edit: неизвестный автор")

        embed = disnake.Embed(
            title="✏ Изменено",
            description=f"**Автор:** {before.author.mention}\n**Канал:** {getattr(before.channel, 'mention', str(before.channel))}\n**Было:**\n{(before.content or '')[:500]}\n**Стало:**\n{(after.content or '')[:500]}",
            color=disnake.Color.blue(),
            timestamp=disnake.utils.utcnow()
        )
        try:
            await self.bot.log_dispatcher.send("messages", embed)
        except Exception as e:
            print(f"Logs: не удалось отправить в log_dispatcher on_message_edit: {e}")
        try:
            await log_event("message_edit", f"{before.author.id}|{before.content or ''}->{after.content or ''}")
        except Exception as e:
            print(f"Logs: не удалось записать событие в БД on_message_edit: {e}")

def setup(bot):
    bot.add_cog(Logs(bot))
