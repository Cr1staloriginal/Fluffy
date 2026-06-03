import aiosqlite
from pathlib import Path
import os
from typing import Optional

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/database.db")
DB_PATH = Path(DATABASE_PATH)


async def init_db() -> None:
    """Инициализация таблиц и загрузка фраз из файла"""
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
        # Добавляем колонку display_name, если её нет
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

    # Автоматическая загрузка фраз из templates.txt
    await load_phrases_from_file()


async def load_phrases_from_file():
    """Загружает фразы из templates.txt в таблицу phrases, если она пуста"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT COUNT(*) FROM phrases") as cur:
            count = (await cur.fetchone())[0]
        if count > 0:
            print("[DB] В таблице phrases уже есть фразы, загрузка не требуется.")
            return

    templates_path = Path(__file__).parent / "templates.txt"
    if not templates_path.exists():
        print("[DB] Файл templates.txt не найден, загрузка фраз отменена.")
        return

    # Читаем файл построчно
    with open(templates_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("[DB] Файл templates.txt пуст или не содержит фраз.")
        return

    # Фильтруем: оставляем только строки, содержащие {nick} (чтобы не загружать мусор)
    phrases = [line for line in lines if "{nick}" in line]
    if not phrases:
        print("[DB] В файле templates.txt нет ни одной фразы с {nick}. Статус не сможет подставлять имена.")
        return

    async with aiosqlite.connect(str(DB_PATH)) as db:
        for phrase in phrases:
            try:
                await db.execute("INSERT OR IGNORE INTO phrases (text) VALUES (?)", (phrase,))
            except Exception as e:
                print(f"[DB] Ошибка вставки фразы: {e}")
        await db.commit()

    print(f"[DB] Загружено {len(phrases)} фраз из templates.txt в таблицу phrases.")


async def update_user_display_name(user_id: int, display_name: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "UPDATE users SET display_name = ?, last_seen = CURRENT_TIMESTAMP WHERE user_id = ?",
            (display_name, user_id)
        )
        await db.commit()


async def get_random_phrase() -> str:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute("SELECT text FROM phrases ORDER BY RANDOM() LIMIT 1") as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return row[0]
            # Фallback на случай, если таблица пуста
            return "🐾 {nick} приветствует тебя!"


async def log_event(event_type: str, payload: str) -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO logs (event_type, payload) VALUES (?, ?)",
            (event_type, payload),
        )
        await db.commit()


async def add_user(user_id: int, username: str, display_name: str = "") -> None:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, display_name) VALUES (?, ?, ?)",
            (user_id, username, display_name)
        )
        await db.commit()