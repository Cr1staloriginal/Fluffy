"""SQLite storage for server-scoped XP, levels, and achievements."""
from __future__ import annotations

import time
from typing import Any

import aiosqlite

from database import DB_PATH
from utils.progression_math import earned_achievement_keys, level_for_xp

ACHIEVEMENT_LABELS = {
    "level_1": "Первый уровень",
    "level_5": "Пятый уровень",
    "level_10": "Десятый уровень",
    "level_25": "Ветеран Fluffy Town",
    "messages_100": "100 сообщений",
    "messages_1000": "1000 сообщений",
}


async def ensure_progression_schema() -> None:
    """Create new tables without altering or deleting existing bot data."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_progress (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                messages_count INTEGER NOT NULL DEFAULT 0,
                last_xp_at REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_achievements (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                achievement_key TEXT NOT NULL,
                earned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, achievement_key)
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_guild_progress_leaderboard "
            "ON guild_progress(guild_id, xp DESC)"
        )
        await db.commit()


async def record_message(
    guild_id: int,
    user_id: int,
    xp_gain: int,
    *,
    now: float | None = None,
    cooldown_seconds: int = 60,
) -> dict[str, Any]:
    """Count a message and award XP at most once per cooldown per member/server."""
    timestamp = time.time() if now is None else now
    newly_earned: list[str] = []
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT OR IGNORE INTO guild_progress (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        async with db.execute(
            "SELECT xp, level, messages_count, last_xp_at FROM guild_progress "
            "WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()

        old_xp, old_level, old_messages, last_xp_at = row
        messages_count = old_messages + 1
        xp_awarded = timestamp - last_xp_at >= cooldown_seconds
        xp = old_xp + (max(0, xp_gain) if xp_awarded else 0)
        level = level_for_xp(xp)
        if xp_awarded:
            await db.execute(
                "UPDATE guild_progress SET xp = ?, level = ?, messages_count = ?, "
                "last_xp_at = ? WHERE guild_id = ? AND user_id = ?",
                (xp, level, messages_count, timestamp, guild_id, user_id),
            )
        else:
            await db.execute(
                "UPDATE guild_progress SET messages_count = ? "
                "WHERE guild_id = ? AND user_id = ?",
                (messages_count, guild_id, user_id),
            )

        for key in sorted(earned_achievement_keys(level, messages_count)):
            cursor = await db.execute(
                "INSERT OR IGNORE INTO guild_achievements "
                "(guild_id, user_id, achievement_key) VALUES (?, ?, ?)",
                (guild_id, user_id, key),
            )
            if cursor.rowcount:
                newly_earned.append(key)
        await db.commit()

    return {
        "xp": xp,
        "level": level,
        "previous_level": old_level,
        "level_up": level > old_level,
        "messages_count": messages_count,
        "xp_awarded": xp_awarded,
        "new_achievements": newly_earned,
    }


async def get_progress(guild_id: int, user_id: int) -> dict[str, int]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "SELECT xp, level, messages_count FROM guild_progress "
            "WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM guild_achievements WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            achievements = (await cursor.fetchone())[0]
    if row is None:
        return {"xp": 0, "level": 0, "messages_count": 0, "achievements": 0}
    return {
        "xp": row[0],
        "level": row[1],
        "messages_count": row[2],
        "achievements": achievements,
    }


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, int, int, int]]:
    safe_limit = max(1, min(int(limit), 25))
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "SELECT user_id, xp, level, messages_count FROM guild_progress "
            "WHERE guild_id = ? ORDER BY xp DESC, level DESC LIMIT ?",
            (guild_id, safe_limit),
        ) as cursor:
            return await cursor.fetchall()


async def get_achievements(guild_id: int, user_id: int) -> list[tuple[str, str]]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            "SELECT achievement_key, earned_at FROM guild_achievements "
            "WHERE guild_id = ? AND user_id = ? ORDER BY earned_at",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
    return [(key, earned_at) for key, earned_at in rows]
