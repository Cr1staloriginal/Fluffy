import disnake
from disnake.ext import commands
import os

OWNER_ID = int(os.getenv("OWNER_ID", 0))

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="команды", description="📋 Показать список доступных вам команд")
    async def show_commands(self, inter: disnake.ApplicationCommandInteraction):
        """Отображает команды, доступные текущему пользователю"""
        member = inter.author
        is_owner = member.id == OWNER_ID

        all_commands = self.bot.slash_commands
        available_commands = []

        for cmd in all_commands:
            if getattr(cmd, "hidden", False):
                continue

            # Проверка на владельца (команды с @commands.is_owner())
            owner_only = False
            for check in cmd.checks:
                if "is_owner" in str(check):
                    owner_only = True
                    break
            if owner_only and not is_owner:
                continue

            # Проверка прав default_member_permissions
            required_perms = cmd.default_member_permissions
            if required_perms and required_perms.value != 0:
                if isinstance(member, disnake.Member):
                    if not member.guild_permissions.value & required_perms.value:
                        continue
                else:
                    continue

            available_commands.append(cmd)

        available_commands.sort(key=lambda c: c.name)

        embed = disnake.Embed(
            title="📚 Доступные команды",
            description=f"Всего команд: {len(available_commands)}",
            color=disnake.Color.blurple()
        )

        if len(available_commands) > 25:
            chunks = [available_commands[i:i+25] for i in range(0, len(available_commands), 25)]
            for i, chunk in enumerate(chunks):
                cmd_list = "\n".join([f"`/{cmd.name}` — {cmd.description}" for cmd in chunk])
                embed.add_field(name=f"Страница {i+1}", value=cmd_list[:1024], inline=False)
        else:
            cmd_text = "\n".join([f"`/{cmd.name}` — {cmd.description}" for cmd in available_commands])
            embed.description = cmd_text[:4096]

        embed.set_footer(text=f"Запросил: {member.display_name}", icon_url=member.display_avatar.url)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="помощь", description="❓ Подробная помощь по конкретной команде")
    async def command_help(self, inter: disnake.ApplicationCommandInteraction, команда: str):
        """Показывает описание и параметры команды"""
        cmd = self.bot.get_slash_command(команда)
        if not cmd:
            await inter.response.send_message(f"Команда `/{команда}` не найдена.", ephemeral=True)
            return

        member = inter.author
        is_owner = member.id == OWNER_ID

        if not is_owner and cmd.default_member_permissions and cmd.default_member_permissions.value != 0:
            if isinstance(member, disnake.Member):
                if not member.guild_permissions.value & cmd.default_member_permissions.value:
                    await inter.response.send_message(f"❌ У вас нет прав для использования команды `/{cmd.name}`.", ephemeral=True)
                    return
            else:
                await inter.response.send_message(f"❌ Команда `/{cmd.name}` недоступна в личных сообщениях.", ephemeral=True)
                return

        embed = disnake.Embed(
            title=f"/{cmd.name}",
            description=cmd.description or "Нет описания",
            color=disnake.Color.green()
        )
        if cmd.options:
            params = []
            for opt in cmd.options:
                required = "обязательный" if opt.required else "опциональный"
                params.append(f"`{opt.name}`: {opt.description} ({required})")
            embed.add_field(name="Параметры", value="\n".join(params), inline=False)

        await inter.response.send_message(embed=embed)

def setup(bot: commands.InteractionBot):
    bot.add_cog(HelpCog(bot))