"""Ручной квест Fluffy Town: ответы, очки и рейтинг."""
from __future__ import annotations
import re
from datetime import datetime, timezone
import aiosqlite
import disnake
from disnake.ext import commands
from database import DB_PATH

def normalize_answer(value: str) -> str:
    value = value.upper().replace("Ё", "Е")
    return re.sub(r"[^0-9A-ZА-Я]", "", value)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class EventQuest(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS event_quest_state (
                guild_id INTEGER PRIMARY KEY, is_open INTEGER NOT NULL DEFAULT 0,
                started_at TEXT, closed_at TEXT)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS event_quest_codes (
                guild_id INTEGER NOT NULL, code TEXT NOT NULL, points INTEGER NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY (guild_id, code))""")
            await db.execute("""CREATE TABLE IF NOT EXISTS event_quest_participants (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id))""")
            await db.execute("""CREATE TABLE IF NOT EXISTS event_quest_solves (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, code TEXT NOT NULL,
                points INTEGER NOT NULL, solved_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, code))""")
            await db.commit()

    async def is_open(self, guild_id: int) -> bool:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT is_open FROM event_quest_state WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
        return bool(row and row[0])

    @staticmethod
    def find_role(guild: disnake.Guild, role_name: str) -> disnake.Role | None:
        """Find a role by its exact name, ignoring surrounding whitespace/case."""
        target = role_name.strip().casefold()
        return next((role for role in guild.roles if role.name.strip().casefold() == target), None)

    async def assign_event_role(
        self, guild: disnake.Guild, member: disnake.Member, role_name: str
    ) -> str | None:
        """Assign an event role if it exists and the bot has permission to manage it."""
        role = self.find_role(guild, role_name)
        if role is None:
            return f"Роль «{role_name}» не найдена — создай её на сервере."
        if role in member.roles:
            return None
        try:
            await member.add_roles(role, reason="Квест Fluffy Town")
        except disnake.Forbidden:
            return f"Не удалось выдать роль «{role_name}». Проверь право «Управлять ролями» и расположение роли Fluffy выше неё."
        except disnake.HTTPException:
            return f"Discord не смог выдать роль «{role_name}». Попробуй проверить настройки ролей."
        return None

    @commands.slash_command(name="event_join", description="Зарегистрироваться в квесте «Тайна пропавшего хвоста»")
    async def event_join(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        if not await self.is_open(inter.guild.id):
            return await inter.response.send_message("🐾 Регистрация и приём ответов сейчас закрыты. Следи за объявлениями Fluffy Town!", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT 1 FROM event_quest_participants WHERE guild_id=? AND user_id=?", (inter.guild.id, inter.author.id)) as cur:
                exists = await cur.fetchone()
            if exists:
                return await inter.response.send_message("🕯️ Ты уже зарегистрирован! Ищи подсказки и отправляй ответы командой /event_answer.", ephemeral=True)
            await db.execute("INSERT INTO event_quest_participants(guild_id,user_id,joined_at) VALUES(?,?,?)", (inter.guild.id, inter.author.id, utc_now()))
            await db.commit()
        role_warning = await self.assign_event_role(
            inter.guild, inter.author, "🎃・Участник квеста"
        )
        message = "🎃 Ты в игре! Ищи спрятанные подсказки в каналах сервера. Когда найдёшь кодовое слово, отправь его через /event_answer."
        if role_warning:
            message += f"\n\n⚠️ {role_warning}"
        await inter.response.send_message(message, ephemeral=True)

    @commands.slash_command(name="event_answer", description="Отправить кодовое слово из найденной подсказки")
    async def event_answer(self, inter: disnake.ApplicationCommandInteraction, answer: str):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        if not await self.is_open(inter.guild.id):
            return await inter.response.send_message("🔒 Приём ответов сейчас закрыт.", ephemeral=True)
        code = normalize_answer(answer)
        if not code or len(code) > 80:
            return await inter.response.send_message("Укажи кодовое слово или фразу из подсказки.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT 1 FROM event_quest_participants WHERE guild_id=? AND user_id=?", (inter.guild.id, inter.author.id)) as cur:
                registered = await cur.fetchone()
            if not registered:
                return await inter.response.send_message("Сначала зарегистрируйся через /event_join.", ephemeral=True)
            async with db.execute("SELECT points FROM event_quest_codes WHERE guild_id=? AND code=?", (inter.guild.id, code)) as cur:
                code_row = await cur.fetchone()
            if not code_row:
                return await inter.response.send_message("🌫️ Пока не подходит. Проверь подсказку и попробуй ещё раз.", ephemeral=True)
            async with db.execute("SELECT 1 FROM event_quest_solves WHERE guild_id=? AND user_id=? AND code=?", (inter.guild.id, inter.author.id, code)) as cur:
                solved = await cur.fetchone()
            if solved:
                return await inter.response.send_message("✨ Этот ответ уже засчитан тебе. Повторные очки не выдаются.", ephemeral=True)
            points = int(code_row[0])
            await db.execute("INSERT INTO event_quest_solves(guild_id,user_id,code,points,solved_at) VALUES(?,?,?,?,?)", (inter.guild.id, inter.author.id, code, points, utc_now()))
            await db.commit()
            async with db.execute("SELECT COALESCE(SUM(points),0), COUNT(*) FROM event_quest_solves WHERE guild_id=? AND user_id=?", (inter.guild.id, inter.author.id)) as cur:
                total, count = await cur.fetchone()
        role_warning = await self.assign_event_role(
            inter.guild, inter.author, "🔎・Искатель улик"
        )
        message = f"🔑 Ответ принят! +{points} очков.\nТвой результат: {total} очков, разгадано подсказок: {count}."
        if role_warning:
            message += f"\n\n⚠️ {role_warning}"
        await inter.response.send_message(message, ephemeral=True)

    @commands.slash_command(name="event_rank", description="Посмотреть рейтинг участников квеста")
    async def event_rank(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("""SELECT p.user_id, COALESCE(SUM(s.points),0), COUNT(s.code), p.joined_at
                FROM event_quest_participants p LEFT JOIN event_quest_solves s
                ON s.guild_id=p.guild_id AND s.user_id=p.user_id WHERE p.guild_id=?
                GROUP BY p.user_id ORDER BY 2 DESC, 3 DESC, p.joined_at ASC LIMIT 10""", (inter.guild.id,)) as cur:
                rows = await cur.fetchall()
        embed = disnake.Embed(title="🏆 Рейтинг — Тайна пропавшего хвоста", color=disnake.Color.orange())
        if not rows:
            embed.description = "Пока никто не зарегистрировался. Будь первым через /event_join!"
        else:
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for i, (user_id, points, count, _) in enumerate(rows):
                member = inter.guild.get_member(int(user_id))
                name = disnake.utils.escape_markdown(member.display_name) if member else f"<@{user_id}>"
                place = medals[i] if i < 3 else f"{i + 1}."
                lines.append(f"{place} **{name}** — **{points}** очков · подсказок: {count}")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Результаты сохраняются в базе Fluffy.")
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="event_stats", description="Посмотреть статистику квеста")
    async def event_stats(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT is_open FROM event_quest_state WHERE guild_id=?", (inter.guild.id,)) as cur:
                state = await cur.fetchone()
            async with db.execute("SELECT COUNT(*) FROM event_quest_participants WHERE guild_id=?", (inter.guild.id,)) as cur:
                participants = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM event_quest_codes WHERE guild_id=?", (inter.guild.id,)) as cur:
                codes = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM event_quest_solves WHERE guild_id=?", (inter.guild.id,)) as cur:
                solves = (await cur.fetchone())[0]
        embed = disnake.Embed(title="🕯️ Статистика квеста", color=disnake.Color.orange())
        embed.add_field(name="Статус", value="🟢 Приём ответов открыт" if state and state[0] else "🔒 Приём ответов закрыт", inline=False)
        embed.add_field(name="Участники", value=str(participants))
        embed.add_field(name="Настроенные ответы", value=str(codes))
        embed.add_field(name="Засчитанные ответы", value=str(solves))
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="event_code_add", description="Добавить правильный ответ и количество очков", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_code_add(self, inter: disnake.ApplicationCommandInteraction, answer: str, points: int):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        code = normalize_answer(answer)
        if not code or len(code) > 80:
            return await inter.response.send_message("Ответ должен содержать от 1 до 80 букв или цифр.", ephemeral=True)
        if not 1 <= points <= 100:
            return await inter.response.send_message("Назначь от 1 до 100 очков.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT 1 FROM event_quest_codes WHERE guild_id=? AND code=?", (inter.guild.id, code)) as cur:
                exists = await cur.fetchone()
            if exists:
                return await inter.response.send_message("Этот ответ уже добавлен. Повторное добавление запрещено, чтобы не менять начисления задним числом.", ephemeral=True)
            await db.execute("INSERT INTO event_quest_codes(guild_id,code,points,created_at) VALUES(?,?,?,?)", (inter.guild.id, code, points, utc_now()))
            await db.commit()
        await inter.response.send_message(f"✅ Ответ добавлен: {answer.strip()} — {points} очков. Сообщение видно только тебе.", ephemeral=True)

    @commands.slash_command(name="event_code_list", description="Посмотреть ответы квеста (только организаторам)", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_code_list(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT code,points FROM event_quest_codes WHERE guild_id=? ORDER BY points DESC,code ASC", (inter.guild.id,)) as cur:
                rows = await cur.fetchall()
        description = "\n".join(f"• {code} — {points} очков" for code, points in rows) or "Ответы ещё не добавлены. Используй /event_code_add."
        embed = disnake.Embed(title="🔐 Список правильных ответов", description=description[:4000], color=disnake.Color.dark_grey())
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="event_start", description="Открыть регистрацию и приём ответов", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_start(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT COUNT(*) FROM event_quest_codes WHERE guild_id=?", (inter.guild.id,)) as cur:
                count = (await cur.fetchone())[0]
            if count == 0:
                return await inter.response.send_message("Сначала добавь правильные ответы через /event_code_add.", ephemeral=True)
            await db.execute("""INSERT INTO event_quest_state(guild_id,is_open,started_at,closed_at) VALUES(?,1,?,NULL)
                ON CONFLICT(guild_id) DO UPDATE SET is_open=1,started_at=excluded.started_at,closed_at=NULL""", (inter.guild.id, utc_now()))
            await db.commit()
        await inter.response.send_message("🎃 Квест открыт! Участники могут использовать /event_join и /event_answer.", ephemeral=True)

    @commands.slash_command(name="event_close", description="Закрыть приём ответов", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_close(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""INSERT INTO event_quest_state(guild_id,is_open,closed_at) VALUES(?,0,?)
                ON CONFLICT(guild_id) DO UPDATE SET is_open=0,closed_at=excluded.closed_at""", (inter.guild.id, utc_now()))
            await db.commit()
        await inter.response.send_message("🔒 Приём ответов закрыт. Результаты сохранены; рейтинг доступен через /event_rank.", ephemeral=True)



    @commands.slash_command(name="event_code_remove", description="Удалить неверно добавленный ответ до начала квеста", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_code_remove(self, inter: disnake.ApplicationCommandInteraction, answer: str):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        code = normalize_answer(answer)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute("SELECT 1 FROM event_quest_solves WHERE guild_id=? AND code=? LIMIT 1", (inter.guild.id, code)) as cur:
                has_solves = await cur.fetchone()
            if has_solves:
                return await inter.response.send_message("Этот ответ уже засчитывался. Удаление запрещено, чтобы не испортить рейтинг.", ephemeral=True)
            cur = await db.execute("DELETE FROM event_quest_codes WHERE guild_id=? AND code=?", (inter.guild.id, code))
            await db.commit()
            removed = cur.rowcount > 0
        if removed:
            await inter.response.send_message("🗑️ Ответ удалён из списка квеста.", ephemeral=True)
        else:
            await inter.response.send_message("Такой ответ не найден.", ephemeral=True)

    @commands.slash_command(name="event_reset", description="Сбросить тестовые результаты и список участников", default_member_permissions=disnake.Permissions(manage_guild=True))
    @commands.has_guild_permissions(manage_guild=True)
    async def event_reset(self, inter: disnake.ApplicationCommandInteraction):
        if not inter.guild:
            return await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM event_quest_solves WHERE guild_id=?", (inter.guild.id,))
            await db.execute("DELETE FROM event_quest_participants WHERE guild_id=?", (inter.guild.id,))
            await db.execute("""INSERT INTO event_quest_state(guild_id,is_open,closed_at) VALUES(?,0,?)
                ON CONFLICT(guild_id) DO UPDATE SET is_open=0,closed_at=excluded.closed_at""", (inter.guild.id, utc_now()))
            await db.commit()
        await inter.response.send_message("♻️ Результаты и участники сброшены. Список кодовых ответов сохранён. Теперь можно начать чистый квест через /event_start.", ephemeral=True)

def setup(bot: commands.InteractionBot):
    bot.add_cog(EventQuest(bot))
