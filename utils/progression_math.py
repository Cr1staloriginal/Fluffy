"""Pure functions for the server-scoped member progression system."""

LEVEL_ACHIEVEMENTS = {
    1: "level_1",
    5: "level_5",
    10: "level_10",
    25: "level_25",
}
MESSAGE_ACHIEVEMENTS = {
    100: "messages_100",
    1000: "messages_1000",
}


def total_xp_for_level(level: int) -> int:
    """Return cumulative XP needed to reach a level (level 0 starts at 0)."""
    if level < 0:
        raise ValueError("level must be >= 0")
    return 100 * level + 50 * level * (level - 1)


def level_for_xp(xp: int) -> int:
    """Calculate a member's level from total XP."""
    if xp < 0:
        raise ValueError("xp must be >= 0")
    level = 0
    while xp >= total_xp_for_level(level + 1):
        level += 1
    return level


def xp_progress(xp: int) -> tuple[int, int, int]:
    """Return (level, XP earned in this level, XP required for next level)."""
    level = level_for_xp(xp)
    current_floor = total_xp_for_level(level)
    next_floor = total_xp_for_level(level + 1)
    return level, xp - current_floor, next_floor - current_floor


def earned_achievement_keys(level: int, messages_count: int) -> set[str]:
    """Return all milestone achievement keys earned at the given totals."""
    earned = {key for threshold, key in LEVEL_ACHIEVEMENTS.items() if level >= threshold}
    earned.update(key for threshold, key in MESSAGE_ACHIEVEMENTS.items() if messages_count >= threshold)
    return earned
