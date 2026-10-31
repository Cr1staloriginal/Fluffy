"""Small, testable helpers for enforcing Fluffy Town-only operation."""


def is_allowed_guild(guild_id: int | None, allowed_guild_id: int) -> bool:
    """Return True only when an event belongs to the configured Fluffy Town guild."""
    return allowed_guild_id > 0 and guild_id == allowed_guild_id
