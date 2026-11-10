"""Small helpers for storing ticket metadata in Discord channel topics."""

from __future__ import annotations


def build_ticket_topic(creator_id: int, category: str, claimed_by: str | int = "") -> str:
    """Build a compact, restart-safe topic value for a ticket channel."""
    safe_category = str(category).replace("|", " ").replace("\n", " ").strip()[:80]
    safe_claim = str(claimed_by).strip() if claimed_by else ""
    if safe_claim and not safe_claim.isdigit():
        safe_claim = ""
    return f"fluffy_ticket|creator={int(creator_id)}|category={safe_category}|claimed_by={safe_claim}"[:1024]


def parse_ticket_topic(topic: str | None) -> dict[str, str]:
    """Parse a Fluffy ticket topic; return an empty mapping for unrelated channels."""
    if not topic or not topic.startswith("fluffy_ticket|"):
        return {}
    values: dict[str, str] = {}
    for part in topic.split("|")[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip()] = value.strip()
    if not values.get("creator", "").isdigit():
        return {}
    return values
