"""Репутация участников с защитой от повторной выдачи."""
import aiosqlite
import disnake
from disnake.ext import commands

from database import DB_PATH


class Reputation(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reputation_scores (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reputation_gives (
                    guild_id INTEGER NOT NULL,
                    giver_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    last_given_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, giver_id)
                )
            """)
            await db.commit()

    @commands.slash_command(name="репутация", description="Показать репутацию участника")
    async def reputation(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = None,
    ):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        target = участник or inter.author
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT score FROM reputation_scores WHERE guild_id=? AND user_id=?",
                (inter.guild.id, target.id),
            ) as cur:
                row = await cur.fetchone()
        score = row[0] if row else 0
        await inter.response.send_message(
            f"🌟 Репутация **{target.display_name}**: **{score}**",
            ephemeral=True,
        )

    @commands.slash_command(name="плюс", description="Поблагодарить участника и повысить его репутацию")
    async def give_reputation(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member,
    ):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        if участник.id == inter.author.id:
            return await inter.response.send_message("Нельзя повышать репутацию самому себе 🙂", ephemeral=True)
        if участник.bot:
            return await inter.response.send_message("Репутацию можно выдавать участникам, а не ботам.", ephemeral=True)

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """SELECT target_id FROM reputation_gives
                   WHERE guild_id=? AND giver_id=?
                     AND datetime(last_given_at) > datetime('now', '-1 day')""",
                (inter.guild.id, inter.author.id),
            ) as cur:
                recent = await cur.fetchone()
            if recent:
                await db.rollback()
                return await inter.response.send_message(
                    "Ты уже выдавал репутацию за последние 24 часа. Попробуй позже 🌙",
                    ephemeral=True,
                )
            await db.execute(
                """INSERT INTO reputation_scores(guild_id, user_id, score) VALUES (?, ?, 1)
                   ON CONFLICT(guild_id, user_id) DO UPDATE SET score=score+1""",
                (inter.guild.id, участник.id),
            )
            await db.execute(
                """INSERT INTO reputation_gives(guild_id, giver_id, target_id, last_given_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(guild_id, giver_id) DO UPDATE SET
                     target_id=excluded.target_id, last_given_at=CURRENT_TIMESTAMP""",
                (inter.guild.id, inter.author.id, участник.id),
            )
            await db.commit()
        await inter.response.send_message(
            f"💖 {inter.author.mention} повысил репутацию {участник.mention} на **+1**!",
            allowed_mentions=disnake.AllowedMentions(users=True, roles=False, everyone=False),
        )


def setup(bot: commands.InteractionBot):
    bot.add_cog(Reputation(bot))
