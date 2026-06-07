import disnake
from disnake.ext import commands
import os
from database import get_warn, update_warn_action, remove_warn, add_warn

MOD_LOG_CHANNEL_ID = int(os.getenv("LOG_CH_MOD", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))
OWNER_ID = int(os.getenv("OWNER_ID", 0))


class WarnActionButtons(disnake.ui.View):
    def __init__(self, warn_id: int, user_id: int, reason: str, message_link: str = None):
        super().__init__(timeout=86400)  # 24 часа
        self.warn_id = warn_id
        self.user_id = user_id
        self.reason = reason
        self.message_link = message_link

    async def get_member(self, guild: disnake.Guild):
        return guild.get_member(self.user_id)

    @disnake.ui.button(label="🔨 Забанить", style=disnake.ButtonStyle.danger, custom_id="warn_ban")
    async def ban_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            await member.ban(reason=f"Автомод: {self.reason}")
            await update_warn_action(self.warn_id, "ban")
            await inter.followup.send(f"🔨 {member.mention} забанен. Причина: {self.reason}")
        else:
            await inter.followup.send(f"❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="👢 Кикнуть", style=disnake.ButtonStyle.danger, custom_id="warn_kick")
    async def kick_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            await member.kick(reason=f"Автомод: {self.reason}")
            await update_warn_action(self.warn_id, "kick")
            await inter.followup.send(f"👢 {member.mention} кикнут. Причина: {self.reason}")
        else:
            await inter.followup.send(f"❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="🔇 Замутить", style=disnake.ButtonStyle.warning, custom_id="warn_mute")
    async def mute_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        guild = inter.guild
        member = await self.get_member(guild)
        if member:
            # Ищем роль "Замьючен" или создаём
            mute_role = disnake.utils.get(guild.roles, name="🔇 Замьючен")
            if not mute_role:
                mute_role = await guild.create_role(name="🔇 Замьючен")
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(mute_role, send_messages=False, speak=False)
                    except:
                        pass
            await member.add_roles(mute_role, reason=f"Автомод: {self.reason}")
            await update_warn_action(self.warn_id, "mute")
            await inter.followup.send(f"🔇 {member.mention} замучен. Причина: {self.reason}")
        else:
            await inter.followup.send(f"❌ Участник не найден на сервере.", ephemeral=True)
        await self.disable_buttons(inter)

    @disnake.ui.button(label="✅ Снять предупреждение", style=disnake.ButtonStyle.success, custom_id="warn_dismiss")
    async def dismiss_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        await remove_warn(self.warn_id)
        await update_warn_action(self.warn_id, "dismissed")
        await inter.followup.send(f"✅ Предупреждение #{self.warn_id} снято с <@{self.user_id}>.")
        await self.disable_buttons(inter)

    async def disable_buttons(self, inter: disnake.MessageInteraction):
        """Отключает все кнопки после нажатия"""
        for child in self.children:
            child.disabled = True
        await inter.edit_original_response(view=self)
        self.stop()


class Warns(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def send_warn_to_mod_channel(self, user_id: int, reason: str, rule_name: str, message_link: str = None):
        """Отправляет embed с предупреждением в канал модерации"""
        channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if not channel:
            print(f"[Warns] Канал {MOD_LOG_CHANNEL_ID} не найден")
            return

        # Добавляем варн в БД
        warn_id = await add_warn(user_id, 0, reason, rule_name, message_link)

        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(user_id) if guild else None
        member_name = member.display_name if member else f"User {user_id}"

        embed = disnake.Embed(
            title="⚠️ НАРУШЕНИЕ ПРАВИЛ",
            description=f"**Участник:** {member_name} (<@{user_id}>)\n**ID:** {user_id}\n**Правило:** {rule_name}\n**Нарушение:** {reason}\n**Варн №:** {warn_id}",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        if message_link:
            embed.add_field(name="📎 Сообщение", value=f"[Перейти к сообщению]({message_link})", inline=False)
        embed.set_footer(text="Нажмите на кнопку, чтобы вынести наказание")

        view = WarnActionButtons(warn_id, user_id, reason, message_link)
        await channel.send(embed=embed, view=view)
        print(f"[Warns] Отправлен варн #{warn_id} для {member_name}")

    @commands.slash_command(name="варны", description="📋 Показать предупреждения участника")
    @commands.has_permissions(moderate_members=True)
    async def warns(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        from database import get_user_warns
        warns = await get_user_warns(member.id)
        if not warns:
            await inter.response.send_message(f"✅ У {member.mention} нет предупреждений.", ephemeral=True)
            return
        embed = disnake.Embed(title=f"📋 Предупреждения {member.display_name}", color=disnake.Color.orange())
        text = ""
        for w in warns[:10]:
            # w = (id, user_id, moderator_id, reason, rule_name, message_link, date, action_taken)
            action = w[7] if len(w) > 7 else "pending"
            action_emoji = "⏳" if action == "pending" else ("✅" if action == "dismissed" else "🔨")
            text += f"{action_emoji} **#{w[0]}** от {w[6][:16]}: {w[3]}\n"
        embed.description = text[:2000]
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="снять_варн", description="🗑️ Снять предупреждение по ID")
    @commands.has_permissions(moderate_members=True)
    async def remove_warn_cmd(self, inter: disnake.ApplicationCommandInteraction, warn_id: int):
        from database import remove_warn
        result = await remove_warn(warn_id)
        if result:
            await inter.response.send_message(f"✅ Предупреждение #{warn_id} снято.", ephemeral=True)
        else:
            await inter.response.send_message(f"❌ Предупреждение #{warn_id} не найдено.", ephemeral=True)


def setup(bot):
    bot.add_cog(Warns(bot))