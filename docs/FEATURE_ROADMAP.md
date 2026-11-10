# Fluffy feature roadmap

This roadmap expands the systems already present in Fluffy. Work is delivered in small pull requests so that `main` stays deployable and each change can be reviewed independently.

## Principles

- Preserve the existing disnake-based architecture and SQLite data.
- Prefer additive migrations and backward-compatible persistent component IDs.
- Keep the bot scoped to Fluffy Town.
- Require explicit staff permissions for moderation and ticket-management actions.
- Add regression tests for pure business logic and run CI before merging.
- Treat live Discord behavior as unverified until tested in the actual server.

## Phase 1 — Ticket workflow

- [x] Ticket categories: general, technical, complaint, partnership.
- [x] Prevent multiple simultaneously open tickets by the same member.
- [x] Staff claim/unclaim action.
- [x] Persist creator, category, and assignee in the channel topic so state survives restarts.
- [x] Restore creator access decisions when closing tickets after a restart.
- [x] Add unit tests for ticket metadata parsing and sanitization.
- [ ] Add transcript export and configurable retention.
- [ ] Add close reasons and optional requester feedback.
- [ ] Add staff response-time and ticket-volume statistics.

## Phase 2 — Logs and moderation audit

- [ ] Add consistent event metadata and actor/target fields.
- [x] Audit-log correlation for role, channel, timeout, kick, and ban events is present in the existing audit cog.
- [x] Add append-only moderation case history with guild-scoped case IDs.
- [x] Add staff-only /cases and /case commands.
- [x] Backfill existing warning records into case history once without deleting the original warnings.
- [x] Add per-event log channel routing with category fallback.\n- [x] Retry transient Discord delivery failures with bounded exponential backoff and jitter (delivery remains best-effort; no persistent queue).
- [ ] Add tests for duplicate-event suppression and permission boundaries.

## Phase 3 — Automod and anti-raid

- [ ] Add per-channel and per-role rule exclusions.
- [ ] Add configurable warning/escalation policies.
- [x] Add an administrator-controlled, persisted runtime override for automatic punishments with an explicit confirmation gate.
- [ ] Add adaptive raid thresholds and a temporary lockdown mode with a clear recovery path.
- [ ] Add a temporary lockdown mode with a clear recovery path.
- [ ] Add reasoned moderation records and regression tests.

## Phase 4 — Verification and member onboarding

- [ ] Add configurable verification methods and timeout handling.
- [ ] Add re-verification flows for role changes or suspicious activity.
- [ ] Improve onboarding status and staff review visibility.
- [ ] Add abuse/rate limits without locking out legitimate members.

## Phase 5 — Temporary voice rooms

- [ ] Add room templates and per-template limits.
- [ ] Add transfer ownership and moderator override.
- [ ] Add temporary room access grants/denials.
- [ ] Add orphan-room cleanup and restart recovery tests.

## Phase 6 — Backups and recovery

- [x] Add versioned backups with SHA-256 integrity metadata and legacy-backup compatibility.
- [x] Add a read-only backup preview command with integrity validation.
- [ ] Add category-level restore options where safe.
- [ ] Add restore audit events and confirmation gates.
- [ ] Test recovery against a disposable database copy.

## Phase 7 — Activity, progression, and economy

- [ ] Add achievements and reward definitions.
- [ ] Add daily/weekly tasks with idempotent reward claims.
- [ ] Add transaction history and economy consistency checks.
- [ ] Add profile summaries and leaderboard filters.
- [ ] Add abuse prevention and tests for reward duplication.

## Phase 8 — Integrations

- [ ] Add per-source delivery state and retry/backoff.
- [ ] Add duplicate publication protection.
- [ ] Add source-specific health/status commands.
- [ ] Add configuration validation and integration tests.

## Phase 9 — Server configuration and operations

- [ ] Consolidate settings validation and defaults.
- [ ] Add safe export/import of guild configuration.
- [ ] Add health diagnostics for database, tasks, and integrations.
- [ ] Add operator-facing diagnostics without exposing secrets.

## Delivery gates

Each phase is delivered in a separate PR. A phase is not considered complete until:
1. automated checks pass;
2. migrations are backward-compatible and preserve existing records;
3. permissions and failure paths are reviewed;
4. live Discord behavior is tested on Fluffy Town where the feature depends on Discord API behavior.
