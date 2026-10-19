"""Бесплатные розыгрыши с кнопкой участия и автоматическим завершением."""
import logging
import random
from datetime import datetime, timedelta, timezone

import aiosqlite
import disnake
from disnake.ext import commands, tasks

from database import DB_PATH

logger = logging.getLogger(__name__)


class GiveawayView(disnake.ui.View):
    def __init__(self, cog=None):
        super().__init__(timeout=None)
        self.cog = cog

    @disnake.ui.button(label="Участвовать", emoji="🎉", style=disnake.ButtonStyle.success, custom_id="fluffy:giveaway:join")
    async def join(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.guild or not inter.message:
            return await inter.response.send_message("Участие доступно только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT ended, ends_at FROM giveaways WHERE message_id=? AND guild_id=?",
                (inter.message.id, inter.guild.id),
            ) as cur:
                giveaway = await cur.fetchone()
            if not giveaway or giveaway[0]:
                return await inter.response.send_message("Этот розыгрыш уже завершён.", ephemeral=True)
            if datetime.fromisoformat(giveaway[1]) <= datetime.now(timezone.utc):
                return await inter.response.send_message("Время участия уже закончилось.", ephemeral=True)
            async with db.execute(
                "SELECT 1 FROM giveaway_entries WHERE message_id=? AND user_id=?",
                (inter.message.id, inter.author.id),
            ) as cur:
                exists = await cur.fetchone()
            if exists:
                await db.execute(
                    "DELETE FROM giveaway_entries WHERE message_id=? AND user_id=?",
                    (inter.message.id, inter.author.id),
                )
                await db.commit()
                return await inter.response.send_message("Ты вышел из розыгрыша.", ephemeral=True)
            await db.execute(
                "INSERT OR IGNORE INTO giveaway_entries(message_id, user_id) VALUES (?, ?)",
                (inter.message.id, inter.author.id),
            )
            await db.commit()
        await inter.response.send_message("🎉 Ты участвуешь! Нажми кнопку ещё раз, чтобы выйти.", ephemeral=True)


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    ends_at TEXT NOT NULL,
                    winners_count INTEGER NOT NULL DEFAULT 1,
                    ended INTEGER NOT NULL DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaway_entries (
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (message_id, user_id)
                )
            """)
            await db.commit()
        self.bot.add_view(GiveawayView(self))
        self.finish_expired.start()

    def cog_unload(self):
        self.finish_expired.cancel()

    @commands.slash_command(name="розыгрыш_создать", description="Создать бесплатный розыгрыш")
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(
        self,
        inter: disnake.ApplicationCommandInteraction,
        приз: str,
        длительность_минут: int,
        победителей: int = 1,
    ):
        if not inter.guild or not isinstance(inter.channel, disnake.TextChannel):
            return await inter.response.send_message("Команда доступна только в текстовом канале сервера.", ephemeral=True)
        if not приз.strip() or len(приз) > 200:
            return await inter.response.send_message("Название приза должно быть от 1 до 200 символов.", ephemeral=True)
        if not 1 <= длительность_минут <= 10080:
            return await inter.response.send_message("Длительность должна быть от 1 минуты до 7 дней.", ephemeral=True)
        if not 1 <= победителей <= 20:
            return await inter.response.send_message("Количество победителей должно быть от 1 до 20.", ephemeral=True)

        ends_at = datetime.now(timezone.utc) + timedelta(minutes=длительность_минут)
        embed = disnake.Embed(
            title="🎉 Розыгрыш Fluffy",
            description=f"**Приз:** {приз.strip()}\n**Победителей:** {победителей}\n**Завершение:** <t:{int(ends_at.timestamp())}:R>\n\nНажми кнопку ниже, чтобы участвовать!",
            color=disnake.Color.gold(),
        )
        embed.set_footer(text="Участие бесплатное. Не отправляй никому пароли или коды.")
        await inter.response.send_message("Создаю розыгрыш…", ephemeral=True)
        message = await inter.channel.send(embed=embed, view=GiveawayView(self))
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """INSERT INTO giveaways(message_id, guild_id, channel_id, prize, ends_at, winners_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message.id, inter.guild.id, inter.channel.id, приз.strip(), ends_at.isoformat(), победителей),
            )
            await db.commit()
        await inter.edit_original_response(content=f"✅ Розыгрыш создан: {message.jump_url}")

    @tasks.loop(seconds=30)
    async def finish_expired(self):
        now = datetime.now(timezone.utc)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT message_id, guild_id, channel_id, prize, winners_count FROM giveaways WHERE ended=0 AND ends_at<=?",
                (now.isoformat(),),
            ) as cur:
                expired = await cur.fetchall()
            for message_id, guild_id, channel_id, prize, winners_count in expired:
                async with db.execute(
                    "SELECT user_id FROM giveaway_entries WHERE message_id=?",
                    (message_id,),
                ) as cur:
                    entrants = [row[0] for row in await cur.fetchall()]
                guild = self.bot.get_guild(guild_id)
                channel = guild.get_channel(channel_id) if guild else None
                if not channel:
                    continue
                try:
                    message = await channel.fetch_message(message_id)
                    view = GiveawayView(self)
                    for item in view.children:
                        item.disabled = True
                    if entrants:
                        winners = random.sample(entrants, min(winners_count, len(entrants)))
                        mentions = ", ".join(f"<@{user_id}>" for user_id in winners)
                        embed = disnake.Embed(
                            title="🎉 Розыгрыш завершён",
                            description=f"**Приз:** {prize}\n**Победитель(и):** {mentions}\nУчастников: {len(entrants)}",
                            color=disnake.Color.green(),
                        )
                        await message.edit(embed=embed, view=view)
                        await db.execute("UPDATE giveaways SET ended=1 WHERE message_id=?", (message_id,))
                        await db.commit()
                        try:
                            await channel.send(f"Поздравляем {mentions}! Вы выиграли **{prize}**.")
                        except (disnake.Forbidden, disnake.HTTPException):
                            logger.exception("Розыгрыш %s завершён, но не удалось отправить объявление победителей", message_id)
                    else:
                        embed = disnake.Embed(
                            title="Розыгрыш завершён",
                            description=f"Приз: **{prize}**\nНикто не участвовал, победителей нет.",
                            color=disnake.Color.orange(),
                        )
                        await message.edit(embed=embed, view=view)
                        await db.execute("UPDATE giveaways SET ended=1 WHERE message_id=?", (message_id,))
                        await db.commit()
                except (disnake.Forbidden, disnake.NotFound, disnake.HTTPException):
                    logger.exception("Не удалось завершить розыгрыш %s", message_id)
            await db.commit()

    @finish_expired.before_loop
    async def before_finish_expired(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.InteractionBot):
    bot.add_cog(Giveaways(bot))
