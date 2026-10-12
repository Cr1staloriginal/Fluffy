"""Manage per-server bot settings from Discord."""
from __future__ import annotations

import datetime

import disnake
from disnake.ext import commands

from database import delete_guild_setting, get_guild_settings, set_guild_setting
from utils.colors import main_color


SETTING_LABELS = {
    "welcome_channel_id": "Канал приветствий",
    "general_channel_id": "Основной канал",
    "rules_channel_id": "Канал правил",
    "verify_channel_id": "Канал верификации",
    "verify_submit_channel_id": "Канал рассмотрения заявок",
    "verified_role_id": "Роль верифицированного участника",
    "rejected_role_id": "Роль отказа в верификации",
    "moderation_role_id": "Роль модерации",
    "news_channel_id": "Канал новостей",
    "news_role_id": "Роль новостей",
    "staff_review_channel_id": "Канал заявок в персонал",
    "auto_message_channel_id": "Канал автосообщений",
    "auto_message_interval": "Интервал автосообщений (минуты)",
    "timezone_offset": "Часовой пояс (UTC offset)",
    "server_birthday": "День рождения сервера (ДД-ММ)",
    "auto_message_enabled": "Автосообщения включены (true/false)",
}

ID_KEYS = {key for key in SETTING_LABELS if key.endswith("_id")}


def validate_value(key: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Значение не может быть пустым.")
    if key in ID_KEYS:
        if not value.isdigit() or int(value) < 0:
            raise ValueError("Для канала или роли укажи числовой ID Discord (или 0, чтобы отключить).")
    elif key == "auto_message_interval":
        if not value.isdigit() or not 5 <= int(value) <= 1440:
            raise ValueError("Интервал должен быть от 5 до 1440 минут.")
    elif key == "timezone_offset":
        try:
            offset = int(value)
        except ValueError as exc:
            raise ValueError("Часовой пояс должен быть целым числом от -12 до +14.") from exc
        if not -12 <= offset <= 14:
            raise ValueError("Часовой пояс должен быть от -12 до +14.")
        value = str(offset)
    elif key == "server_birthday":
        try:
            day, month = map(int, value.split("-", maxsplit=1))
            datetime.date(2000, month, day)
        except (ValueError, TypeError) as exc:
            raise ValueError("Дата должна быть в формате ДД-ММ, например 30-10.") from exc
        value = f"{day:02d}-{month:02d}"
    elif key == "auto_message_enabled":
        normalized = value.lower()
        if normalized not in {"true", "false", "1", "0", "да", "нет", "on", "off"}:
            raise ValueError("Укажи true или false.")
        value = "true" if normalized in {"true", "1", "да", "on"} else "false"
    return value


class ServerSettings(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="настройки", description="⚙️ Настройки Пушистика для этого сервера")
    async def settings(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @settings.sub_command(name="показать", description="Показать сохранённые настройки этого сервера")
    @commands.has_guild_permissions(manage_guild=True)
    async def show(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Эта команда доступна только на сервере.", ephemeral=True)
            return
        settings = await get_guild_settings(inter.guild.id)
        embed = disnake.Embed(
            title=f"⚙️ Настройки — {inter.guild.name}",
            description="Настройки, сохранённые в БД. Пустые значения используют конфигурацию окружения.",
            color=main_color(),
        )
        if not settings:
            embed.add_field(name="Пока пусто", value="Используй /настройки установить, чтобы задать переопределение.", inline=False)
        else:
            for key, value in list(settings.items())[:25]:
                label = SETTING_LABELS.get(key, key)
                embed.add_field(name=label, value=value[:900], inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @settings.sub_command(name="установить", description="Задать настройку для этого сервера")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_value(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ключ: str = commands.Param(choices=SETTING_LABELS),
        значение: str = commands.Param(description="ID, число, дата или true/false"),
    ):
        if inter.guild is None:
            await inter.response.send_message("Эта команда доступна только на сервере.", ephemeral=True)
            return
        try:
            value = validate_value(ключ, значение)
        except ValueError as exc:
            await inter.response.send_message(f"❌ {exc}", ephemeral=True)
            return
        await set_guild_setting(inter.guild.id, ключ, value)
        await inter.response.send_message(
            f"✅ Сохранено: **{SETTING_LABELS[ключ]}** = {value}. "
            "Переопределение записано; модули будут подключаться к этой конфигурации поэтапно.",
            ephemeral=True,
        )

    @settings.sub_command(name="сбросить", description="Удалить переопределение и вернуться к настройке по умолчанию")
    @commands.has_guild_permissions(manage_guild=True)
    async def reset_value(
        self,
        inter: disnake.ApplicationCommandInteraction,
        ключ: str = commands.Param(choices=SETTING_LABELS),
    ):
        if inter.guild is None:
            await inter.response.send_message("Эта команда доступна только на сервере.", ephemeral=True)
            return
        removed = await delete_guild_setting(inter.guild.id, ключ)
        message = (
            f"✅ Переопределение {SETTING_LABELS[ключ]} удалено."
            if removed else f"ℹ️ Для настройки {SETTING_LABELS[ключ]} не было переопределения."
        )
        await inter.response.send_message(message, ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(ServerSettings(bot))
