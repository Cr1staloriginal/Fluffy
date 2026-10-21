"""Custom text commands that server managers can create without editing code."""
from __future__ import annotations

import re

import disnake
from disnake.ext import commands

from database import create_custom_command, delete_custom_command, get_custom_command, list_custom_commands
from utils.colors import main_color

NAME_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="команда", description="🧩 Управление пользовательскими командами")
    async def custom_command(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @custom_command.sub_command(name="создать", description="Создать пользовательскую текстовую команду")
    @commands.has_guild_permissions(manage_guild=True)
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        имя: str = commands.Param(min_length=1, max_length=32),
        ответ: str = commands.Param(description="Текст ответа (до 2000 символов)", max_length=2000),
    ):
        if inter.guild is None:
            await inter.response.send_message("Команды можно создавать только на сервере.", ephemeral=True)
            return
        name = имя.strip().lower()
        if not NAME_PATTERN.fullmatch(name):
            await inter.response.send_message(
                "❌ Имя должно содержать только латинские буквы, цифры, дефис или подчёркивание (1–32 символа).",
                ephemeral=True,
            )
            return
        if not ответ.strip():
            await inter.response.send_message("❌ Ответ не может быть пустым.", ephemeral=True)
            return
        created = await create_custom_command(inter.guild.id, name, ответ.strip(), inter.author.id)
        if not created:
            await inter.response.send_message(
                f"❌ Команда {name} уже существует на этом сервере. Выбери другое имя.",
                ephemeral=True,
            )
            return
        await inter.response.send_message(
            f"✅ Команда {name} создана. Вызов: /команда вызвать имя:{name}.",
            ephemeral=True,
        )

    @custom_command.sub_command(name="вызвать", description="Выполнить пользовательскую команду")
    async def invoke(
        self,
        inter: disnake.ApplicationCommandInteraction,
        имя: str = commands.Param(min_length=1, max_length=32),
    ):
        if inter.guild is None:
            await inter.response.send_message("Эта команда доступна только на сервере.", ephemeral=True)
            return
        response = await get_custom_command(inter.guild.id, имя.strip().lower())
        if response is None:
            await inter.response.send_message("❌ Такая пользовательская команда не найдена.", ephemeral=True)
            return
        await inter.response.send_message(
            response[:2000],
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    @custom_command.sub_command(name="список", description="Показать пользовательские команды сервера")
    async def list_commands(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Эта команда доступна только на сервере.", ephemeral=True)
            return
        rows = await list_custom_commands(inter.guild.id)
        embed = disnake.Embed(title="🧩 Пользовательские команды", color=main_color())
        if not rows:
            embed.description = "Пока нет команд. Администратор может создать их через /команда создать."
        else:
            embed.description = "\n".join(f"• {name} — {response[:90]}" for name, response in rows[:25])
            if len(rows) > 25:
                embed.set_footer(text=f"Показаны первые 25 из {len(rows)} команд")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @custom_command.sub_command(name="удалить", description="Удалить пользовательскую команду")
    @commands.has_guild_permissions(manage_guild=True)
    async def delete(
        self,
        inter: disnake.ApplicationCommandInteraction,
        имя: str = commands.Param(min_length=1, max_length=32),
    ):
        if inter.guild is None:
            await inter.response.send_message("Команды можно удалять только на сервере.", ephemeral=True)
            return
        deleted = await delete_custom_command(inter.guild.id, имя.strip().lower())
        message = f"✅ Команда {имя} удалена." if deleted else f"❌ Команда {имя} не найдена."
        await inter.response.send_message(message, ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(CustomCommands(bot))
