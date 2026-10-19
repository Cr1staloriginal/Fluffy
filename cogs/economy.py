"""Простая экономика сервера: баланс, ежедневная награда, переводы и предметы."""
from datetime import datetime, timezone

import aiosqlite
import disnake
from disnake.ext import commands

from database import DB_PATH


DAILY_REWARD = 100
STARTING_BALANCE = 0
SHOP_ITEMS = (
    ("cookie", "🍪 Печенька", 50, "Маленький пушистый перекус."),
    ("plush", "🧸 Плюш", 250, "Коллекционный плюшевый сувенир."),
    ("aura", "✨ Аура", 500, "Редкий блестящий предмет для коллекции."),
)


class Economy(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy_accounts (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
                    last_daily TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy_shop (
                    item_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL CHECK(price >= 0),
                    description TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy_inventory (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                    PRIMARY KEY (guild_id, user_id, item_key)
                )
            """)
            await db.executemany(
                "INSERT OR IGNORE INTO economy_shop(item_key, name, price, description) VALUES (?, ?, ?, ?)",
                SHOP_ITEMS,
            )
            await db.commit()

    async def ensure_account(self, db, guild_id: int, user_id: int):
        await db.execute(
            "INSERT OR IGNORE INTO economy_accounts(guild_id, user_id, balance) VALUES (?, ?, ?)",
            (guild_id, user_id, STARTING_BALANCE),
        )
        await db.commit()

    @commands.slash_command(name="баланс", description="Показать баланс участника")
    async def balance(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = None,
    ):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        target = участник or inter.author
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await self.ensure_account(db, inter.guild.id, target.id)
            async with db.execute(
                "SELECT balance FROM economy_accounts WHERE guild_id=? AND user_id=?",
                (inter.guild.id, target.id),
            ) as cur:
                row = await cur.fetchone()
        await inter.response.send_message(
            f"💰 Баланс **{target.display_name}**: **{row[0]:,}** 🪙".replace(",", " "),
            ephemeral=True,
        )

    @commands.slash_command(name="ежедневно", description="Получить ежедневные 100 монет")
    async def daily(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        today = datetime.now(timezone.utc).date().isoformat()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await self.ensure_account(db, inter.guild.id, inter.author.id)
            async with db.execute(
                "SELECT last_daily FROM economy_accounts WHERE guild_id=? AND user_id=?",
                (inter.guild.id, inter.author.id),
            ) as cur:
                row = await cur.fetchone()
            if row and row[0] == today:
                return await inter.response.send_message("Ты уже забрал ежедневную награду. Попробуй завтра 🌙", ephemeral=True)
            await db.execute(
                "UPDATE economy_accounts SET balance=balance+?, last_daily=? WHERE guild_id=? AND user_id=?",
                (DAILY_REWARD, today, inter.guild.id, inter.author.id),
            )
            await db.commit()
        await inter.response.send_message(f"🎁 Ежедневная награда: **+{DAILY_REWARD}** 🪙", ephemeral=True)

    @commands.slash_command(name="перевести", description="Перевести монеты участнику сервера")
    async def transfer(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member,
        сумма: int,
    ):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        if сумма <= 0:
            return await inter.response.send_message("Сумма должна быть больше нуля.", ephemeral=True)
        if участник.id == inter.author.id or участник.bot:
            return await inter.response.send_message("Выбери другого участника, не бота.", ephemeral=True)

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await self.ensure_account(db, inter.guild.id, inter.author.id)
            await self.ensure_account(db, inter.guild.id, участник.id)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT balance FROM economy_accounts WHERE guild_id=? AND user_id=?",
                (inter.guild.id, inter.author.id),
            ) as cur:
                row = await cur.fetchone()
            if not row or row[0] < сумма:
                await db.rollback()
                return await inter.response.send_message("Недостаточно монет для перевода.", ephemeral=True)
            await db.execute(
                "UPDATE economy_accounts SET balance=balance-? WHERE guild_id=? AND user_id=?",
                (сумма, inter.guild.id, inter.author.id),
            )
            await db.execute(
                "UPDATE economy_accounts SET balance=balance+? WHERE guild_id=? AND user_id=?",
                (сумма, inter.guild.id, участник.id),
            )
            await db.commit()
        await inter.response.send_message(f"💸 Переведено **{сумма:,}** 🪙 участнику {участник.mention}.".replace(",", " "), ephemeral=True)

    @commands.slash_command(name="магазин", description="Посмотреть предметы за монеты")
    async def shop(self, inter: disnake.ApplicationCommandInteraction):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT name, price, description FROM economy_shop ORDER BY price") as cur:
                items = await cur.fetchall()
        embed = disnake.Embed(title="🛍️ Магазин Fluffy", color=disnake.Color.gold())
        for name, price, description in items:
            embed.add_field(name=f"{name} — {price} 🪙", value=description, inline=False)
        embed.set_footer(text="Покупка: /купить предмет")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="купить", description="Купить предмет в магазине")
    async def buy(self, inter: disnake.ApplicationCommandInteraction, предмет: str):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT item_key, name, price FROM economy_shop WHERE lower(name)=lower(?) OR lower(item_key)=lower(?)",
                (предмет.strip(), предмет.strip()),
            ) as cur:
                item = await cur.fetchone()
            if not item:
                async with db.execute("SELECT name FROM economy_shop ORDER BY price") as cur:
                    names = [row[0] for row in await cur.fetchall()]
                return await inter.response.send_message(
                    "Не нашёл предмет. Доступно: " + ", ".join(names) + ". Открой /магазин.",
                    ephemeral=True,
                )
            item_key, name, price = item
            await self.ensure_account(db, inter.guild.id, inter.author.id)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT balance FROM economy_accounts WHERE guild_id=? AND user_id=?",
                (inter.guild.id, inter.author.id),
            ) as cur:
                row = await cur.fetchone()
            if not row or row[0] < price:
                await db.rollback()
                return await inter.response.send_message("Недостаточно монет.", ephemeral=True)
            await db.execute(
                "UPDATE economy_accounts SET balance=balance-? WHERE guild_id=? AND user_id=?",
                (price, inter.guild.id, inter.author.id),
            )
            await db.execute(
                """INSERT INTO economy_inventory(guild_id, user_id, item_key, quantity)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(guild_id, user_id, item_key)
                   DO UPDATE SET quantity=quantity+1""",
                (inter.guild.id, inter.author.id, item_key),
            )
            await db.commit()
        await inter.response.send_message(f"✅ Куплено: **{name}** за **{price}** 🪙", ephemeral=True)

    @commands.slash_command(name="инвентарь", description="Показать коллекцию предметов")
    async def inventory(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = None,
    ):
        if inter.guild is None:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        target = участник or inter.author
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                """SELECT s.name, i.quantity FROM economy_inventory i
                   JOIN economy_shop s ON s.item_key=i.item_key
                   WHERE i.guild_id=? AND i.user_id=? AND i.quantity>0 ORDER BY s.price""",
                (inter.guild.id, target.id),
            ) as cur:
                items = await cur.fetchall()
        if not items:
            return await inter.response.send_message(f"У **{target.display_name}** пока пустая коллекция.", ephemeral=True)
        text = "\n".join(f"• {name} × {quantity}" for name, quantity in items)
        await inter.response.send_message(f"🎒 **Коллекция {target.display_name}**\n{text}", ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(Economy(bot))
