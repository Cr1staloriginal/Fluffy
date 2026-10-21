<<<<<<< HEAD
import disnake
from disnake.ext import commands
import os

OWNER_ID = int(os.getenv("OWNER_ID", 0))
=======
"""Categorized slash-command help for Fluffy."""
from __future__ import annotations

import disnake
from disnake.ext import commands

from utils.colors import main_color


CATEGORY_RULES = [
    ("🛡️ Модерация", ("варн", "мут", "бан", "кик", "антирейд", "автомод")),
    ("🎫 Поддержка", ("тикет", "идея", "предложение", "верификац")),
    ("👥 Участники", ("фурри", "инфо", "аватар", "пользователь", "сервер", "топ")),
    ("🎉 Развлечения", ("игры", "развлеч", "мило", "комплимент", "шутка", "таро", "рандом")),
    ("📣 Публикации", ("новость", "объявление", "скажи", "навигация")),
    ("🎵 Музыка", ("музыка", "плей", "очередь", "пауза", "пропустить")),
    ("⚙️ Настройки", ("настройки", "сезон", "автосообщение", "команда")),
    ("👑 Персонал", ("персонал", "должность", "бэкап", "восстановить", "др")),
]


def category_for(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    for category, needles in CATEGORY_RULES:
        if any(needle in text for needle in needles):
            return category
    return "📚 Прочее"


def can_view_command(command, member) -> bool:
    required = getattr(command, "default_member_permissions", None)
    if not required:
        return True
    required_value = getattr(required, "value", None)
    if required_value is None or required_value == 0:
        return True
    if not isinstance(member, disnake.Member):
        return False
    return (member.guild_permissions.value & required_value) == required_value

>>>>>>> f42350e9a5a07c86594c560b74edb37ad7a73064

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

<<<<<<< HEAD
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
=======
    @commands.slash_command(name="команды", description="📋 Список команд по категориям")
    async def show_commands(self, inter: disnake.ApplicationCommandInteraction):
        grouped: dict[str, list[str]] = {}
        commands_seen = set()
        for command in self.bot.slash_commands:
            name = getattr(command, "name", "")
            if not name or name in commands_seen or getattr(command, "hidden", False):
                continue
            if not can_view_command(command, inter.author):
                continue
            commands_seen.add(name)
            category = category_for(name, getattr(command, "description", "") or "")
            description = (getattr(command, "description", "") or "Без описания").replace("\n", " ")
            grouped.setdefault(category, []).append(f"**/{name}** — {description[:100]}")

        embed = disnake.Embed(
            title="🐾 Справочник Пушистика",
            description="Команды сгруппированы по назначению. Для подробностей используй /помощь.",
            color=main_color(),
        )
        for category, entries in grouped.items():
            value = "\n".join(sorted(entries))
            while value:
                chunk = value[:1000]
                split_at = chunk.rfind("\n")
                if split_at > 0 and len(value) > 1000:
                    chunk = chunk[:split_at]
                embed.add_field(name=category, value=chunk, inline=False)
                value = value[len(chunk):].lstrip("\n")
                if len(embed.fields) >= 25:
                    break
            if len(embed.fields) >= 25:
                break
        embed.set_footer(text=f"Запросил: {inter.author.display_name}")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="помощь", description="❓ Подробная помощь по slash-команде")
    async def command_help(
        self,
        inter: disnake.ApplicationCommandInteraction,
        команда: str = commands.Param(description="Название команды без символа /"),
    ):
        name = команда.strip().lstrip("/")
        command = self.bot.get_slash_command(name)
        if command is None:
            await inter.response.send_message(
                f"Команда /{name} не найдена. Открой /команды, чтобы посмотреть список.",
                ephemeral=True,
            )
            return
        if not can_view_command(command, inter.author):
            await inter.response.send_message(
                f"🔒 Команда /{name} требует дополнительных прав Discord.",
                ephemeral=True,
            )
            return

        embed = disnake.Embed(
            title=f"📘 /{command.name}",
            description=getattr(command, "description", None) or "Описание пока не добавлено.",
            color=main_color(),
        )
        options = getattr(command, "options", []) or []
        if options:
            lines = []
            for option in options:
                required = "обязательный" if getattr(option, "required", False) else "необязательный"
                lines.append(
                    f"• {option.name} — {getattr(option, 'description', '') or 'без описания'} ({required})"
                )
            embed.add_field(name="Параметры", value="\n".join(lines)[:1024], inline=False)
        embed.add_field(name="Категория", value=category_for(command.name, command.description or ""), inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(HelpCog(bot))
>>>>>>> f42350e9a5a07c86594c560b74edb37ad7a73064
