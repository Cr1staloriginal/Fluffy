import aiosqlite
from pathlib import Path
import os
from typing import Optional

# Путь к БД из переменной окружения или по умолчанию
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/database.db")
DB_PATH = Path(DATABASE_PATH)

async def init_db() -> None:
    """Инициализация всех таблиц и миграция"""
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
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Добавляем колонку display_name, если её нет (миграция)
        async with db.execute("PRAGMA table_info(users)") as cur:
            columns = [row[1] for row in await cur.fetchall()]
            if 'display_name' not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''")

        # Таблица phrases
        await db.execute("""
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT UNIQUE
            )
        """)
        # Таблица logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица tickets
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ========== Работа с пользователями ==========
async def add_user(user_id: int, username: str, display_name: str = "") -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, display_name) VALUES (?, ?, ?)",
            (user_id, username, display_name)
        )
        await db.commit()

async def update_user_display_name(user_id: int, display_name: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "UPDATE users SET display_name = ?, last_seen = CURRENT_TIMESTAMP WHERE user_id = ?",
            (display_name, user_id)
        )
        await db.commit()

async def get_user_display_name(user_id: int) -> str:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT display_name, username FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return row[0]
            elif row:
                return row[1]
            else:
                return f"User#{user_id}"

async def update_user(user_id: int, **kwargs) -> None:
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values())
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            f"UPDATE users SET {fields} WHERE user_id=?",
            (*values, user_id)
        )
        await db.commit()

# ========== Фразы ==========
async def add_phrase(text: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("INSERT OR IGNORE INTO phrases (text) VALUES (?)", (text,))
        await db.commit()

async def get_random_phrase() -> str:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT text FROM phrases ORDER BY RANDOM() LIMIT 1") as cur:
            row = await cur.fetchone()
            return row[0] if row else "🐾 {nick} приветствует тебя!"

# ========== Логи событий ==========
async def log_event(event_type: str, payload: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO logs (event_type, payload) VALUES (?, ?)",
            (event_type, payload)
        )
        await db.commit()