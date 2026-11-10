"""Permission-based ticket staff discovery for Fluffy Town."""

from __future__ import annotations

# Include common moderation and administration capabilities. This avoids relying
# on role names and automatically covers newly-created staff roles.
STAFF_PERMISSION_FLAGS = (
    "administrator",
    "manage_guild",
    "manage_channels",
    "manage_messages",
    "manage_threads",
    "moderate_members",
    "kick_members",
    "ban_members",
    "view_audit_log",
)

LEGACY_STAFF_ROLE_NAMES = {
    "мэр",
    "старейшина города",
    "городской советник",
    "старший страж порядка",
    "городской страж",
}


def _has_staff_permissions(permissions) -> bool:
    if permissions is None:
        return False
    return any(bool(getattr(permissions, flag, False)) for flag in STAFF_PERMISSION_FLAGS)


def get_staff_roles(guild) -> list:
    """Return every server role that has staff permissions or a legacy staff name."""
    roles = getattr(guild, "roles", ())
    return [
        role
        for role in roles
        if (
            str(getattr(role, "name", "")).casefold() in LEGACY_STAFF_ROLE_NAMES
            or _has_staff_permissions(getattr(role, "permissions", None))
        )
    ]


def is_staff_member(member) -> bool:
    """Check the member's effective permissions and assigned staff roles."""
    if member is None:
        return False
    if _has_staff_permissions(getattr(member, "guild_permissions", None)):
        return True
    return any(
        str(getattr(role, "name", "")).casefold() in LEGACY_STAFF_ROLE_NAMES
        or _has_staff_permissions(getattr(role, "permissions", None))
        for role in getattr(member, "roles", ())
    )
