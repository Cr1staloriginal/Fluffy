# Moderation case history

Fluffy stores an append-only, guild-scoped history for moderation actions.

## Recorded events

- Automod warnings (the system actor is shown when no human moderator initiated the action).
- Ban, kick, and mute actions selected from a warning action card.
- Warning dismissals selected from a warning action card.

## Staff commands

- `/cases member:<member> limit:<1-25>` — show a member's latest cases.
- `/case case_id:<id>` — inspect one case, including actor, reason, source, date, and message link.

Both commands require the Discord `moderate_members` permission and return results ephemerally.

## Data and migration

- Case IDs are append-only and scoped to a guild.
- Existing rows in the `warns` table are backfilled once using a unique legacy source reference.
- Existing warning records are not deleted or modified by the backfill.
- New history rows are additive; this does not replace the existing warning system.
