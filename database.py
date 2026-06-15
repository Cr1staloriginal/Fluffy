import aiosqlite
from pathlib import Path
import os
import datetime
from typing import Optional

# Попытка взять путь к БД из config.py, если он есть, иначе из переменных окружения или значения по умолчанию
try:
    from config import DATABASE_PATH as CONFIG_DB_PATH
except Exception:
    CONFIG_DB_PATH = None

DATABASE_PATH = os.getenv("DATABASE_PATH", CONFIG_DB_PATH or "data/database.db")
DB_PATH = Path(DATABASE_PATH)


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Таблица users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                display_name TEXT DEFAULT '',
                verified INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                messages_sent INTEGER DEFAULT 0,
                voice_minutes INTEGER DEFAULT 0,
                cookies_received INTEGER DEFAULT 0,
                voice_join_time TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        async with db.execute("PRAGMA table_info(users)") as cur:
            columns = [row[1] for row in await cur.fetchall()]
            if 'display_name' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''")
            if 'messages_sent' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN messages_sent INTEGER DEFAULT 0")
            if 'voice_minutes' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN voice_minutes INTEGER DEFAULT 0")
            if 'cookies_received' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN cookies_received INTEGER DEFAULT 0")
            if 'voice_join_time' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN voice_join_time TIMESTAMP")

        # Таблица phrases
        await db.execute("""
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                rule_name TEXT,
                message_link TEXT,
                date TEXT,
                action_taken TEXT DEFAULT 'pending'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id INTEGER PRIMARY KEY,
                birthday TEXT NOT NULL,
                set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица suggestions (без channel_id и message_id – добавим ниже)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'open'
            )
        """)
        # Добавляем колонки channel_id и message_id, если их нет
        async with db.execute("PRAGMA table_info(suggestions)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
            if 'channel_id' not in cols:
                await db.execute("ALTER TABLE suggestions ADD COLUMN channel_id INTEGER")
            if 'message_id' not in cols:
                await db.execute("ALTER TABLE suggestions ADD COLUMN message_id INTEGER")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_votes (
                suggestion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                rating INTEGER NOT NULL,
                PRIMARY KEY (suggestion_id, user_id)
            )
        """)
        await db.commit()

    await load_phrases_from_file()


async def load_phrases_from_file():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT COUNT(*) FROM phrases") as cur:
            count = (await cur.fetchone())[0]
        if count > 0:
            return
    templates_path = Path(__file__).parent / "templates.txt"
    if not templates_path.exists():
        print("[DB] templates.txt не найден")
        return
    with open(templates_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and "{nick}" in line]
    async with aiosqlite.connect(str(DB_PATH)) as db:
        for line in lines:
            await db.execute("INSERT OR IGNORE INTO phrases (text) VALUES (?)", (line,))
        await db.commit()
    print(f"[DB] Загружено {len(lines)} фраз")


# ========== Пользователи и валюта ==========
async def update_user_display_name(user_id: int, display_name: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "UPDATE users SET display_name = ?, last_seen = CURRENT_TIMESTAMP WHERE user_id = ?",
            (display_name, user_id)
        )
        await db.commit()

async def add_coins(user_id: int, amount: int) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_coins(user_id: int) -> int:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT points FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def set_coins(user_id: int, amount: int) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET points = ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


# ========== Фразы ==========
async def get_random_phrase() -> str:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT text FROM phrases ORDER BY RANDOM() LIMIT 1") as cur:
            row = await cur.fetchone()
            return row[0] if row else "🐾 {nick} приветствует тебя!"


# ========== Логирование ==========
async def log_event(event_type: str, payload: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO logs (event_type, payload) VALUES (?, ?)",
            (event_type, payload)
        )
        await db.commit()


# ========== Варны ==========
async def add_warn(user_id: int, moderator_id: int, reason: str = None, rule_name: str = None, message_link: str = None) -> int:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("""
            INSERT INTO warns (user_id, moderator_id, reason, rule_name, message_link, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, moderator_id, reason, rule_name, message_link, datetime.datetime.now().isoformat()))
        await db.commit()
        return cursor.lastrowid

async def get_user_warns(user_id: int) -> list:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT * FROM warns WHERE user_id = ? ORDER BY date DESC", (user_id,)) as cur:
            return await cur.fetchall()

async def remove_warn(warn_id: int) -> bool:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("DELETE FROM warns WHERE id = ?", (warn_id,))
        await db.commit()
        return cursor.rowcount > 0


# ========== Дни рождения ==========
async def set_birthday(user_id: int, birthday: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT OR REPLACE INTO birthdays (user_id, birthday) VALUES (?, ?)",
            (user_id, birthday)
        )
        await db.commit()

async def get_birthday(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT birthday FROM birthdays WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def delete_birthday(user_id: int) -> bool:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_today_birthdays(today: str) -> list[int]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT user_id FROM birthdays WHERE birthday = ?", (today,)) as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]


# ========== Статистика активности ==========
async def increment_messages(user_id: int, delta: int = 1) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET messages_sent = messages_sent + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()

async def add_voice_minutes(user_id: int, minutes: int) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET voice_minutes = voice_minutes + ? WHERE user_id = ?", (minutes, user_id))
        await db.commit()

async def add_cookies(user_id: int, delta: int = 1) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET cookies_received = cookies_received + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()

async def set_voice_join_time(user_id: int, timestamp: Optional[float]) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE users SET voice_join_time = ? WHERE user_id = ?", (timestamp, user_id))
        await db.commit()

async def get_voice_join_time(user_id: int) -> Optional[float]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT voice_join_time FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT messages_sent, voice_minutes, cookies_received FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()


# ========== Предложения ==========
async def add_suggestion(author_id: int, text: str) -> int:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("INSERT INTO suggestions (author_id, text) VALUES (?, ?)", (author_id, text))
        await db.commit()
        return cursor.lastrowid

async def get_suggestion(suggestion_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)) as cur:
            return await cur.fetchone()

async def update_suggestion_message(suggestion_id: int, channel_id: int, message_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE suggestions SET channel_id = ?, message_id = ? WHERE id = ?", (channel_id, message_id, suggestion_id))
        await db.commit()

async def add_vote(suggestion_id: int, user_id: int, type_: str, rating: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            INSERT OR REPLACE INTO suggestion_votes (suggestion_id, user_id, type, rating)
            VALUES (?, ?, ?, ?)
        """, (suggestion_id, user_id, type_, rating))
        await db.commit()

async def get_suggestion_votes_by_type(suggestion_id: int, type_: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT rating FROM suggestion_votes WHERE suggestion_id = ? AND type = ?", (suggestion_id, type_)) as cur:
            rows = await cur.fetchall()
            if not rows:
                return (None, 0)
            ratings = [r[0] for r in rows]
            avg = sum(ratings) / len(ratings)
            return (avg, len(ratings))

async def close_suggestion(suggestion_id: int, status: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE suggestions SET status = ? WHERE id = ?", (status, suggestion_id))
        await db.commit()
