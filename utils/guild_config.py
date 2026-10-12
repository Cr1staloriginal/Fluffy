"""Helpers for per-server configuration with environment-variable fallbacks."""
from __future__ import annotations

import os
from typing import Optional

from database import get_guild_setting


async def get_guild_config(guild_id: int, key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a guild-specific override, falling back to the matching environment variable."""
    value = await get_guild_setting(guild_id, key)
    if value is not None:
        return value
    return os.getenv(key.upper(), default)


async def get_guild_config_int(guild_id: int, key: str, default: int = 0) -> int:
    value = await get_guild_config(guild_id, key)
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


async def get_guild_config_bool(guild_id: int, key: str, default: bool = False) -> bool:
    value = await get_guild_config(guild_id, key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "да"}
