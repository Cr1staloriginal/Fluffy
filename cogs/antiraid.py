import asyncio
import logging
import copy
import disnake
from disnake.ext import commands, tasks
import time
import json
import hashlib
import datetime
import os
from collections import deque, defaultdict
from datetime import datetime
import aiosqlite
from database import DB_PATH, log_event

logger = logging.getLogger(__name__)

# ---------------------- КОНФИГУРАЦИЯ (на русском) ----------------------
RAID_CONFIG = {
    "создание_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "изменение_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "удаление_каналов": {"limit": 5, "time_window": 1, "punishment": "clear_roles_kick"},
    "создание_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "изменение_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "удаление_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "бан": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "спам": {"limit": 10, "time_window": 5, "punishment": "timeout_3h"}
}

def is_auto_punish_enabled(value: str | None = None) -> bool:
    """Fail closed: automatic moderation is disabled unless explicitly enabled."""
    raw_value = os.getenv("ANTIRAID_AUTO_PUNISH") if value is None else value
    return str(raw_value if raw_value is not None else "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


# Destructive actions are opt-in. Enable explicitly only after testing permissions
# and role hierarchy on a separate Discord server.
ANTIRAID_AUTO_PUNISH = is_auto_punish_enabled()

BACKUP_FORMAT_VERSION = 2


def _backup_digest(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_backup_document(payload: dict) -> dict:
    """Wrap a guild snapshot in a versioned document with a SHA-256 integrity digest."""
    document = copy.deepcopy(payload)
    document["format_version"] = BACKUP_FORMAT_VERSION
    document.pop("integrity", None)
    document["integrity"] = {
        "algorithm": "sha256",
        "digest": _backup_digest(document),
    }
    return document


def validate_backup_document(document, expected_guild_id: int) -> tuple[bool, str]:
    """Validate legacy and versioned backups before any restore-side effects."""
    if not isinstance(document, dict):
        return False, "корень бэкапа должен быть JSON-объектом"
    if document.get("id_сервера") != expected_guild_id:
        return False, "бэкап принадлежит другому серверу"
    for key in ("категории", "каналы", "роли"):
        if not isinstance(document.get(key), list):
            return False, f"поле «{key}» отсутствует или имеет неверный формат"

    # Only files with no version marker are legacy. An explicit downgrade
    # must never bypass the integrity check for a versioned backup.
    if "format_version" not in document:
        if "integrity" in document:
            return False, "у бэкапа есть контрольная сумма, но отсутствует версия формата"
        return True, "legacy"
    version = document.get("format_version")
    if not isinstance(version, int) or version != BACKUP_FORMAT_VERSION:
        return False, "неподдерживаемая версия формата бэкапа"
    if version == BACKUP_FORMAT_VERSION:
        integrity = document.get("integrity")
        if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
            return False, "отсутствует контрольная сумма бэкапа"
        payload = {key: value for key, value in document.items() if key != "integrity"}
        if integrity.get("digest") != _backup_digest(payload):
            return False, "контрольная сумма не совпадает; файл мог быть повреждён"
    return True, "ok"

# ---------------------- ОСНОВНОЙ КОГ ----------------------
class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.config = copy.deepcopy(RAID_CONFIG)
        self.trackers = {
            "создание_каналов": defaultdict(deque),
            "изменение_каналов": defaultdict(deque),
            "удаление_каналов": defaultdict(deque),
            "создание_ролей": defaultdict(deque),
            "изменение_ролей": defaultdict(deque),
            "удаление_ролей": defaultdict(deque),
            "бан": defaultdict(deque),
            "спам": defaultdict(deque),
        }
        self.raid_active = False
        self.last_triggered = defaultdict(dict)

    async def cog_load(self):
        """Load persisted anti-raid settings; keep defaults for missing actions."""
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS antiraid_config (
                    action_type TEXT PRIMARY KEY,
                    limit_value INTEGER NOT NULL,
                    time_window INTEGER NOT NULL,
                    punishment TEXT NOT NULL
                )
            """)
            async with db.execute(
                "SELECT action_type, limit_value, time_window, punishment FROM antiraid_config"
            ) as cur:
                for action_type, limit_value, time_window, punishment in await cur.fetchall():
                    if action_type in self.config and punishment in {"clear_roles_kick", "timeout_3h"}:
                        self.config[action_type] = {
                            "limit": max(0, min(int(limit_value), 100)),
                            "time_window": max(1, min(int(time_window), 300)),
                            "punishment": punishment,
                        }
            await db.commit()

    async def save_config(self):
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.executemany(
                """INSERT INTO antiraid_config(action_type, limit_value, time_window, punishment)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(action_type) DO UPDATE SET
                     limit_value=excluded.limit_value,
                     time_window=excluded.time_window,
                     punishment=excluded.punishment""",
                [
                    (action, cfg["limit"], cfg["time_window"], cfg["punishment"])
                    for action, cfg in self.config.items()
                ],
            )
            await db.commit()

    # ---------- ОБРАБОТЧИКИ СОБЫТИЙ ----------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        observed_at = time.time()
        actor = await self.find_actor(channel.guild, disnake.AuditLogAction.channel_create, channel.id)
        await self.handle_action("создание_каналов", channel.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        observed_at = time.time()
        actor = await self.find_actor(after.guild, disnake.AuditLogAction.channel_update, after.id)
        await self.handle_action("изменение_каналов", after.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        observed_at = time.time()
        actor = await self.find_actor(channel.guild, disnake.AuditLogAction.channel_delete, channel.id)
        await self.handle_action("удаление_каналов", channel.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        observed_at = time.time()
        actor = await self.find_actor(role.guild, disnake.AuditLogAction.role_create, role.id)
        await self.handle_action("создание_ролей", role.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        observed_at = time.time()
        actor = await self.find_actor(after.guild, disnake.AuditLogAction.role_update, after.id)
        await self.handle_action("изменение_ролей", after.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        observed_at = time.time()
        actor = await self.find_actor(role.guild, disnake.AuditLogAction.role_delete, role.id)
        await self.handle_action("удаление_ролей", role.guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        observed_at = time.time()
        actor = await self.find_actor(guild, disnake.AuditLogAction.ban, user.id)
        await self.handle_action("бан", guild, actor, observed_at=observed_at)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return
        await self.handle_action("спам", message.guild, message.author)

    async def find_actor(self, guild: disnake.Guild, action, target_id: int):
        """Resolve the exact audit-log actor, retrying briefly for Discord audit-log lag."""
        for attempt in range(4):
            try:
                async for entry in guild.audit_logs(limit=10, action=action):
                    if getattr(entry.target, "id", None) != target_id:
                        continue
                    age = (disnake.utils.utcnow() - entry.created_at).total_seconds()
                    if 0 <= age <= 15:
                        return entry.user
            except (disnake.Forbidden, disnake.HTTPException):
                return None
            if attempt < 3:
                await asyncio.sleep(0.35)
        return None

    # ---------- ОСНОВНАЯ ЛОГИКА ----------
    async def handle_action(self, action_type: str, guild: disnake.Guild, actor, observed_at: float | None = None):
        config = self.config.get(action_type)
        # Bot accounts can be attackers too; only ignore missing actors and Fluffy itself.
        if actor is None or (guild.me and getattr(actor, "id", None) == guild.me.id):
            return
        if not config or config.get("limit", 0) == 0:
            return

        now = observed_at if observed_at is not None else time.time()
        tracker = self.trackers[action_type][(guild.id, actor.id)]
        tracker.append(now)

        while tracker and now - tracker[0] > config["time_window"]:
            tracker.popleft()

        last = self.last_triggered[(guild.id, actor.id)].get(action_type, 0)
        if len(tracker) >= config["limit"] and now - last >= config["time_window"]:
            self.last_triggered[(guild.id, actor.id)][action_type] = now
            await self.apply_punishment(guild, actor, config["punishment"], action_type)

    async def apply_punishment(self, guild: disnake.Guild, actor, punishment: str, action_type: str):
        if actor is None or (guild.me and getattr(actor, "id", None) == guild.me.id):
            return

        # Audit-log entries often expose User instead of Member; resolve the member
        # before choosing kick vs ban, so ordinary members are not banned by mistake.
        member = actor if isinstance(actor, disnake.Member) else guild.get_member(actor.id)
        if member is None and isinstance(actor, disnake.User):
            try:
                member = await guild.fetch_member(actor.id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                member = None

        if getattr(actor, "id", None) == guild.owner_id:
            await self.log_raid(guild, action_type, actor, "пропущено: владелец сервера")
            return

        if not ANTIRAID_AUTO_PUNISH:
            await self.log_raid(guild, action_type, actor, "только журналирование — включите ANTIRAID_AUTO_PUNISH=true")
            return

        reason = f"Fluffy anti-raid: {action_type}"
        result = "наказание не выполнено"
        if punishment == "clear_roles_kick":
            if member is not None:
                try:
                    await member.kick(reason=reason)
                    result = "участник/бот кикнут"
                except (disnake.Forbidden, disnake.HTTPException) as exc:
                    result = f"не удалось кикнуть: {type(exc).__name__}"
            else:
                result = "нарушитель уже вышел или не найден; автоматический бан не выполнялся"
        elif punishment == "timeout_3h" and member is not None:
            try:
                until = disnake.utils.utcnow() + datetime.timedelta(hours=3)
                await member.timeout(until, reason=reason)
                result = "тайм-аут 3 часа"
            except (disnake.Forbidden, disnake.HTTPException) as exc:
                result = f"не удалось выдать тайм-аут: {type(exc).__name__}"

        await self.log_raid(guild, action_type, actor, result)

    async def log_raid(self, guild: disnake.Guild, action_type: str, actor, punishment: str):
        actor_id = getattr(actor, "id", 0)
        actor_label = actor.mention if hasattr(actor, "mention") else str(actor)
        embed = disnake.Embed(
            title="🚨 Сработала анти-рейд система!",
            description=f"**Действие:** {action_type}\n"
                        f"**Нарушитель:** {actor_label} ({actor_id})\n"
                        f"**Результат:** {punishment}",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_footer(text=f"Fluffy Anti-Raid • Guild ID: {guild.id}")
        await self.bot.log_dispatcher.send("mod", embed)
        try:
            await log_event("antiraid", f"{guild.id}|{action_type}|{actor_id}|{punishment}")
        except Exception:
            logger.exception("Не удалось сохранить событие Anti-Raid в SQLite")

    # ---------- БЭКАП СЕРВЕРА ----------
    @commands.slash_command(name="бэкап", description="📦 Создать бэкап структуры сервера", default_member_permissions=disnake.Permissions(administrator=True))
    @commands.has_permissions(administrator=True)
    async def backup(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        data = {
            "название_сервера": guild.name,
            "id_сервера": guild.id,
            "создан": datetime.now().isoformat(),
            "категории": [],
            "каналы": [],
            "роли": []
        }

        for category in guild.categories:
            cat_data = {
                "название": category.name,
                "позиция": category.position,
                "id": category.id
            }
            data["категории"].append(cat_data)

        for channel in guild.channels:
            if isinstance(channel, disnake.TextChannel):
                ch_data = {
                    "тип": "текстовый",
                    "название": channel.name,
                    "позиция": channel.position,
                    "тема": channel.topic,
                    "задержка": channel.slowmode_delay,
                    "категория_id": channel.category_id,
                    "id": channel.id
                }
                data["каналы"].append(ch_data)
            elif isinstance(channel, disnake.VoiceChannel):
                ch_data = {
                    "тип": "голосовой",
                    "название": channel.name,
                    "позиция": channel.position,
                    "битрейт": channel.bitrate,
                    "лимит": channel.user_limit,
                    "категория_id": channel.category_id,
                    "id": channel.id
                }
                data["каналы"].append(ch_data)

        for role in guild.roles:
            if role.name == "@everyone":
                continue
            role_data = {
                "название": role.name,
                "цвет": role.color.value,
                "права": role.permissions.value,
                "позиция": role.position,
                "упоминаемый": role.mentionable,
                "отдельная": role.hoist,
                "id": role.id
            }
            data["роли"].append(role_data)

        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        filename = f"backup_{guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)

        data = build_backup_document(data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        await inter.edit_original_response(content=f"✅ Бэкап сервера сохранён: `{filename}`")

    # ---------- ВОССТАНОВЛЕНИЕ ИЗ БЭКАПА ----------
    @commands.slash_command(name="восстановить_бэкап", description="🔄 Восстановить структуру сервера из бэкапа", default_member_permissions=disnake.Permissions(administrator=True))
    @commands.has_permissions(administrator=True)
    async def restore_backup(
        self,
        inter: disnake.ApplicationCommandInteraction,
        имя_файла: str = None
    ):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        if not os.path.exists(backup_dir):
            await inter.edit_original_response("❌ Папка с бэкапами не найдена.")
            return

        if not имя_файла:
            prefix = f"backup_{guild.id}_"
            files = [f for f in os.listdir(backup_dir) if f.startswith(prefix) and f.endswith(".json")]
            if not files:
                await inter.edit_original_response("❌ Нет бэкапов для этого сервера.")
                return
            files.sort(reverse=True)
            имя_файла = files[0]

        # Only allow backups created for this guild; reject traversal and arbitrary file paths.
        prefix = f"backup_{guild.id}_"
        if os.path.basename(имя_файла) != имя_файла or not имя_файла.startswith(prefix) or not имя_файла.endswith(".json"):
            await inter.edit_original_response(content="❌ Допускаются только файлы бэкапа этого сервера.")
            return
        filepath = os.path.join(backup_dir, имя_файла)
        if not os.path.exists(filepath):
            await inter.edit_original_response("❌ Файл бэкапа не найден.")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            await inter.edit_original_response("❌ Не удалось прочитать JSON-файл бэкапа.")
            return

        valid, validation_message = validate_backup_document(data, guild.id)
        if not valid:
            await inter.edit_original_response(f"❌ Бэкап не прошёл проверку: {validation_message}.")
            return

        # Словарь для сопоставления старых ID категорий с новыми
        category_map = {}

        # 1. Создаём категории
        for cat_data in data["категории"]:
            try:
                new_cat = await guild.create_category(
                    name=cat_data["название"],
                    position=cat_data["позиция"]
                )
                category_map[cat_data["id"]] = new_cat
            except Exception as e:
                print(f"Ошибка создания категории {cat_data['название']}: {e}")

        # 2. Создаём каналы внутри категорий
        for ch_data in data["каналы"]:
            try:
                category = category_map.get(ch_data.get("категория_id"))
                if ch_data["тип"] == "текстовый":
                    await guild.create_text_channel(
                        name=ch_data["название"],
                        category=category,
                        position=ch_data["позиция"],
                        topic=ch_data.get("тема", ""),
                        slowmode_delay=ch_data.get("задержка", 0)
                    )
                elif ch_data["тип"] == "голосовой":
                    await guild.create_voice_channel(
                        name=ch_data["название"],
                        category=category,
                        position=ch_data["позиция"],
                        bitrate=ch_data.get("битрейт", 64000),
                        user_limit=ch_data.get("лимит", 0)
                    )
            except Exception as e:
                print(f"Ошибка создания канала {ch_data['название']}: {e}")

        # 3. Создаём роли (порядок не критичен)
        for role_data in data["роли"]:
            try:
                await guild.create_role(
                    name=role_data["название"],
                    color=disnake.Color(role_data["цвет"]),
                    permissions=disnake.Permissions(role_data["права"]),
                    mentionable=role_data["упоминаемый"],
                    hoist=role_data["отдельная"]
                )
            except:
                pass

        await inter.edit_original_response("✅ Бэкап успешно восстановлен! Структура сервера восстановлена.")

    @commands.slash_command(
        name="предпросмотр_бэкапа",
        description="🔎 Проверить бэкап и показать, что в нём сохранено",
    )
    @commands.has_permissions(administrator=True)
    async def preview_backup(
        self,
        inter: disnake.ApplicationCommandInteraction,
        имя_файла: str = None,
    ):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        prefix = f"backup_{guild.id}_"
        if not имя_файла:
            try:
                files = [name for name in os.listdir(backup_dir) if name.startswith(prefix) and name.endswith(".json")]
            except OSError:
                files = []
            if not files:
                await inter.edit_original_response("📭 Бэкапы для этого сервера не найдены.")
                return
            имя_файла = sorted(files, reverse=True)[0]

        if os.path.basename(имя_файла) != имя_файла or not имя_файла.startswith(prefix) or not имя_файла.endswith(".json"):
            await inter.edit_original_response("❌ Допускаются только имена бэкапов текущего сервера.")
            return

        filepath = os.path.join(backup_dir, имя_файла)
        try:
            with open(filepath, "r", encoding="utf-8") as backup_file:
                data = json.load(backup_file)
        except (OSError, json.JSONDecodeError):
            await inter.edit_original_response("❌ Не удалось прочитать выбранный бэкап.")
            return

        valid, message = validate_backup_document(data, guild.id)
        if not valid:
            await inter.edit_original_response(f"❌ Проверка не пройдена: {message}.")
            return

        version = data.get("format_version")
        validation_label = (
            "Проверка целостности: **успешна**"
            if version == BACKUP_FORMAT_VERSION
            else "Формат legacy: структура проверена, контрольной суммы нет"
        )
        embed = disnake.Embed(
            title="🔎 Предпросмотр бэкапа",
            description=f"`{имя_файла}`\n{validation_label}",
            color=disnake.Color.green(),
            timestamp=disnake.utils.utcnow(),
        )
        embed.add_field(name="Версия формата", value=str(version), inline=True)
        embed.add_field(name="Категории", value=str(len(data["категории"])), inline=True)
        embed.add_field(name="Каналы", value=str(len(data["каналы"])), inline=True)
        embed.add_field(name="Роли", value=str(len(data["роли"])), inline=True)
        embed.set_footer(text="Предпросмотр ничего не изменяет на сервере")
        await inter.edit_original_response(embed=embed)

    # ---------- КОМАНДА ДЛЯ СПИСКА БЭКАПОВ ----------
    @commands.slash_command(name="список_бэкапов", description="📋 Показать список бэкапов для этого сервера")
    @commands.has_permissions(administrator=True)
    async def list_backups(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        if not os.path.exists(backup_dir):
            await inter.edit_original_response("📭 Нет сохранённых бэкапов.")
            return

        prefix = f"backup_{guild.id}_"
        files = [f for f in os.listdir(backup_dir) if f.startswith(prefix) and f.endswith(".json")]
        if not files:
            await inter.edit_original_response("📭 Нет бэкапов для этого сервера.")
            return

        files.sort(reverse=True)
        embed = disnake.Embed(
            title="📋 Список бэкапов",
            description=f"Для сервера **{guild.name}**",
            color=disnake.Color.blurple()
        )
        for f in files[:10]:
            embed.add_field(
                name=f,
                value=f"🕐 {f.split('_')[-1].replace('.json', '')}",
                inline=False
            )
        await inter.edit_original_response(embed=embed)

    # ---------- НАСТРОЙКА КОНФИГА ----------
    @commands.slash_command(name="антирейд", description="🛡️ Настройка анти-рейд системы")
    @commands.has_permissions(administrator=True)
    async def antiraid(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @antiraid.sub_command(name="настроить", description="Изменить настройки анти-рейда")
    @commands.has_permissions(administrator=True)
    async def set_config(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тип: str = commands.Param(choices=["создание_каналов", "изменение_каналов", "удаление_каналов",
                                           "создание_ролей", "изменение_ролей", "удаление_ролей", "бан", "спам"]),
        лимит: int = commands.Param(description="Количество действий до срабатывания (0 = выкл)"),
        окно: int = commands.Param(description="Временное окно в секундах"),
        наказание: str = commands.Param(choices=["кик", "таймаут_3ч"])
    ):
        punishment_map = {
            "кик": "clear_roles_kick",
            "таймаут_3ч": "timeout_3h"
        }
        if not 0 <= лимит <= 100 or not 1 <= окно <= 300:
            await inter.response.send_message(
                "❌ Лимит должен быть от 0 до 100, окно — от 1 до 300 секунд.",
                ephemeral=True,
            )
            return
        self.config[тип] = {"limit": лимит, "time_window": окно, "punishment": punishment_map[наказание]}
        await self.save_config()
        await inter.response.send_message(
            f"✅ Настройки для **{тип}** обновлены:\n"
            f"Лимит: {лимит}\nОкно: {окно} сек\nНаказание: {наказание}",
            ephemeral=True
        )

    @antiraid.sub_command(name="статус", description="Показать текущие настройки анти-рейда")
    @commands.has_permissions(administrator=True)
    async def show_config(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="🛡️ Настройки анти-рейда", color=disnake.Color.blurple())
        for action, cfg in self.config.items():
            status = "✅ Вкл" if cfg["limit"] > 0 else "❌ Выкл"
            punishment_map = {
                "clear_roles_kick": "кик",
                "timeout_3h": "таймаут 3 часа"
            }
            embed.add_field(
                name=action.replace("_", " ").capitalize(),
                value=f"Лимит: {cfg['limit']}\nОкно: {cfg['time_window']}с\nНаказание: {punishment_map.get(cfg['punishment'], cfg['punishment'])}",
                inline=True
            )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @antiraid.sub_command(name="сброс", description="Сбросить все настройки к значениям по умолчанию")
    @commands.has_permissions(administrator=True)
    async def reset_config(self, inter: disnake.ApplicationCommandInteraction):
        self.config = copy.deepcopy(RAID_CONFIG)
        await self.save_config()
        await inter.response.send_message("✅ Настройки анти-рейда сброшены до значений по умолчанию.", ephemeral=True)

def setup(bot: commands.InteractionBot):
    bot.add_cog(AntiRaid(bot))