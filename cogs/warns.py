import disnake
from disnake.ext import commands
import os
from database import add_warn, remove_warn, get_user_warns
from utils.colors import main_color

MOD_LOG_CHANNEL_ID = int(os.getenv("LOG_CH_MOD", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))

class WarnActionButtons(disnake.ui.View):
    def __init__(self, warn_id: int, user_id: int, reason: str, warn_count: int = 0):
        super().__init__(timeout=86400)
        self.warn_id = warn_id
        self.user_id = user_id
        self.reason = reason
        self.warn_count = warn_count

    async def get_member(self, guild: disnake.Guild):
        return guild.get_member(self.user_id)

    @disnake.ui.button(label="🔨 Забанить", style=disnake.ButtonStyle.danger)
    async def ban_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Проверяем, есть ли у пользователя право на бан
        if not inter.author.guild_permissions.ban_members:
            await inter.response.send_message("❌ У вас нет права `ban_members`.", ephemeral=True)
            return
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            await member.ban(reason=f"Решение модератора {inter.author} (ID: {inter.author.id}): {self.reason}")
            await inter.followup.send(f"🔨 {member.mention} забанен. Модератор: {inter.author.mention}")
            log_embed = disnake.Embed(
                title="🔨 Бан",
                description=f"**Участник:** {member.mention}\n**Модератор:** {inter.author.mention} (ID: {inter.author.id})",
                color=disnake.Color.red(),
                timestamp=disnake.utils.utcnow()
            )
            log_embed.add_field(name="Причина", value=self.reason, inline=False)
            log_embed.set_footer(text=f"Варн #{self.warn_count}")
            await inter.bot.log_dispatcher.send("mod", log_embed)
        else:
            await inter.followup.send("❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="👢 Кикнуть", style=disnake.ButtonStyle.danger)
    async def kick_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.kick_members:
            await inter.response.send_message("❌ У вас нет права `kick_members`.", ephemeral=True)
            return
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            await member.kick(reason=f"Решение модератора {inter.author} (ID: {inter.author.id}): {self.reason}")
            await inter.followup.send(f"👢 {member.mention} кикнут. Модератор: {inter.author.mention}")
            log_embed = disnake.Embed(
                title="👢 Кик",
                description=f"**Участник:** {member.mention}\n**Модератор:** {inter.author.mention} (ID: {inter.author.id})",
                color=disnake.Color.orange(),
                timestamp=disnake.utils.utcnow()
            )
            log_embed.add_field(name="Причина", value=self.reason, inline=False)
            log_embed.set_footer(text=f"Варн #{self.warn_count}")
            await inter.bot.log_dispatcher.send("mod", log_embed)
        else:
            await inter.followup.send("❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="🔇 Замутить", style=disnake.ButtonStyle.secondary)
    async def mute_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.manage_roles:
            await inter.response.send_message("❌ У вас нет права `manage_roles`.", ephemeral=True)
            return
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            mute_role = disnake.utils.get(guild.roles, name="🔇 Замьючен")
            if not mute_role:
                mute_role = await guild.create_role(name="🔇 Замьючен")
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(mute_role, send_messages=False, speak=False)
                    except:
                        pass
            await member.add_roles(mute_role, reason=f"Решение модератора {inter.author} (ID: {inter.author.id}): {self.reason}")
            await inter.followup.send(f"🔇 {member.mention} замучен. Модератор: {inter.author.mention}")
            log_embed = disnake.Embed(
                title="🔇 Мут",
                description=f"**Участник:** {member.mention}\n**Модератор:** {inter.author.mention} (ID: {inter.author.id})\n**Длительность:** бессрочно (до снятия)",
                color=disnake.Color.orange(),
                timestamp=disnake.utils.utcnow()
            )
            log_embed.add_field(name="Причина", value=self.reason, inline=False)
            log_embed.set_footer(text=f"Варн #{self.warn_count}")
            await inter.bot.log_dispatcher.send("mod", log_embed)
        else:
            await inter.followup.send("❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="✅ Снять предупреждение", style=disnake.ButtonStyle.success)
    async def dismiss_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Для снятия варна достаточно права moderate_members или manage_messages
        if not (inter.author.guild_permissions.moderate_members or inter.author.guild_permissions.manage_messages):
            await inter.response.send_message("❌ У вас нет права `moderate_members` или `manage_messages`.", ephemeral=True)
            return
        await inter.response.defer()
        if await remove_warn(self.warn_id):
            await inter.followup.send(f"✅ Предупреждение #{self.warn_id} снято с <@{self.user_id}>.")
        else:
            await inter.followup.send(f"⚠️ Предупреждение #{self.warn_id} не найдено.", ephemeral=True)
        await self.disable_buttons(inter)

    async def disable_buttons(self, inter: disnake.MessageInteraction):
        for child in self.children:
            child.disabled = True
        await inter.edit_original_response(view=self)
        self.stop()

class Warns(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def send_warn_to_mod_channel(self, user_id: int, reason: str, rule_name: str, message_link: str = None):
        channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if not channel:
            print(f"[Warns] Канал {MOD_LOG_CHANNEL_ID} не найден")
            return

        # Считаем количество варнов у пользователя (для номера)
        user_warns = await get_user_warns(user_id)
        warn_count = len(user_warns) + 1

        warn_id = await add_warn(user_id, 0, reason, rule_name, message_link)
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(user_id) if guild else None
        member_name = member.display_name if member else f"User {user_id}"

        embed = disnake.Embed(
            title=f"⚠️ Предупреждение #{warn_count}",
            description=f"**Участник:** {member_name} (<@{user_id}>)\n**Правило:** {rule_name}\n**Нарушение:** {reason}",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        if message_link:
            embed.add_field(name="📎 Сообщение", value=f"[Перейти к сообщению]({message_link})", inline=False)
        embed.set_footer(text=f"ID участника: {user_id}")

        view = WarnActionButtons(warn_id, user_id, reason, warn_count)
        await channel.send(embed=embed, view=view)

    @commands.slash_command(name="варны", description="📋 Показать предупреждения участника")
    @commands.has_permissions(moderate_members=True)
    async def warns(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        from database import get_user_warns
        warns = await get_user_warns(member.id)
        if not warns:
            await inter.response.send_message(f"✅ У {member.mention} нет предупреждений.", ephemeral=True)
            return
        embed = disnake.Embed(title=f"📋 Предупреждения {member.display_name}", color=main_color())
        text = ""
        for i, w in enumerate(warns[:10], 1):
            text += f"**#{i}** от {w[6][:16]}: {w[3]}\n"
        embed.description = text[:2000]
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="снять_варн", description="🗑️ Снять предупреждение по ID")
    @commands.has_permissions(moderate_members=True)
    async def remove_warn_cmd(self, inter: disnake.ApplicationCommandInteraction, warn_id: int):
        if await remove_warn(warn_id):
            await inter.response.send_message(f"✅ Предупреждение #{warn_id} снято.", ephemeral=True)
        else:
            await inter.response.send_message(f"❌ Предупреждение #{warn_id} не найдено.", ephemeral=True)

def setup(bot):
    bot.add_cog(Warns(bot))