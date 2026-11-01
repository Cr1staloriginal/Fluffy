# Fluffy Logging

Fluffy routes audit events to five dedicated channels. Configure their numeric Discord channel IDs in the hosting environment or the local .env file:

| Environment variable | Channel |
| --- | --- |
| LOG_CH_MEMBERS | 👥 Участники |
| LOG_CH_MESSAGES | 💬 Сообщения |
| LOG_CH_TICKETS | 🎟️ Тикеты |
| LOG_CH_VOICE | 🗣️ Голосовые-каналы |
| LOG_CH_MOD | 💼 Модерация |

Use 0 or leave a value empty to disable that category. The bot reads these values at startup.

## Discord permissions

Give Fluffy access to each log channel:
- View Channel
- Send Messages
- Embed Links
- Read Message History (useful for troubleshooting and future transcript features)

For moderator attribution and server structure audit events, also grant the bot's role **View Audit Log** at the server level. Without this permission, events are still logged, but the initiator is shown as unknown.

The bot already enables the Members, Message Content, and Voice States intents in main.py. Message deletion details depend on Discord delivering a cached message object; Discord does not provide deleted message content for every uncached message.

## Events

- Members: joins, leaves/kicks where distinguishable, nickname changes, role changes, avatar changes, timeout state changes.
- Messages: edits, deletions, bulk deletions, attachments and message links when available.
- Tickets: ticket creation and closure.
- Voice: joins, leaves, moves, server/self mute and deaf, camera, stream, and stage speaking state.
- Moderation: bans, unbans, anti-raid alerts, channel and role creation/deletion/updates, server settings changes, warnings and timeout state changes.

All categories use the shared LogDispatcher. Delivery failures are logged to the bot process log; transient Discord HTTP failures are retried. Events that support it are also stored in the existing SQLite logs table.
