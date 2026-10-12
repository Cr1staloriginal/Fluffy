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


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

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
