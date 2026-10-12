import disnake
from disnake.ext import commands, tasks
import time
import asyncio
import json
import datetime as datetime_module
import os
from collections import deque, defaultdict
from datetime import datetime
import aiosqlite
from database import DB_PATH

# Automatic anti-raid response is enabled by default: the configured threshold
# triggers a kick/timeout. Set ANTIRAID_AUTO_PUNISH=false to run in log-only mode.
AUTO_PUNISH = os.getenv("ANTIRAID_AUTO_PUNISH", "true").strip().lower() in {
    "1", "true", "yes", "on", "да"
}

# ---------------------- КОНФИГУРАЦИЯ (на русском) ----------------------
RAID_CONFIG = {
    "создание_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "изменение_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    # Five channel deletions in one second is treated as an urgent raid.
    "удаление_каналов": {"limit": 5, "time_window": 1, "punishment": "kick"},
    "создание_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "изменение_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "удаление_ролей": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "бан": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "спам": {"limit": 10, "time_window": 5, "punishment": "timeout_3h"}
}

# ---------------------- ОСНОВНОЙ КОГ ----------------------
class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.config = RAID_CONFIG.copy()
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

    # ---------- ОБРАБОТЧИКИ СОБЫТИЙ ----------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        occurred_at = time.monotonic()
        actor = await self.find_actor(channel.guild, disnake.AuditLogAction.channel_create, channel.id)
        await self.handle_action("создание_каналов", channel.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        occurred_at = time.monotonic()
        actor = await self.find_actor(after.guild, disnake.AuditLogAction.channel_update, after.id)
        await self.handle_action("изменение_каналов", after.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        occurred_at = time.monotonic()
        actor = await self.find_actor(channel.guild, disnake.AuditLogAction.channel_delete, channel.id)
        await self.handle_action("удаление_каналов", channel.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        occurred_at = time.monotonic()
        actor = await self.find_actor(role.guild, disnake.AuditLogAction.role_create, role.id)
        await self.handle_action("создание_ролей", role.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        occurred_at = time.monotonic()
        actor = await self.find_actor(after.guild, disnake.AuditLogAction.role_update, after.id)
        await self.handle_action("изменение_ролей", after.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        occurred_at = time.monotonic()
        actor = await self.find_actor(role.guild, disnake.AuditLogAction.role_delete, role.id)
        await self.handle_action("удаление_ролей", role.guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        occurred_at = time.monotonic()
        actor = await self.find_actor(guild, disnake.AuditLogAction.ban, user.id)
        await self.handle_action("бан", guild, actor, occurred_at)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return
        await self.handle_action("спам", message.guild, message.author, time.monotonic())

    async def find_actor(self, guild: disnake.Guild, action, target_id: int):
        """Find the audit-log actor for this exact target, retrying briefly for API lag."""
        for attempt in range(3):
            try:
                async for entry in guild.audit_logs(limit=10, action=action):
                    if getattr(entry.target, "id", None) != target_id:
                        continue
                    if (disnake.utils.utcnow() - entry.created_at).total_seconds() <= 15:
                        return entry.user
            except (disnake.Forbidden, disnake.HTTPException):
                return None
            if attempt < 2:
                await asyncio.sleep(0.35)
        return None

    # ---------- ОСНОВНАЯ ЛОГИКА ----------
    async def handle_action(self, action_type: str, guild: disnake.Guild, actor, occurred_at: float | None = None):
        config = self.config.get(action_type)
        # Actor attribution requires audit-log access. Bot accounts are valid
        # suspects too, so do not ignore them just because actor.bot is true.
        if actor is None:
            return
        if not config or config.get("limit", 0) == 0:
            return

        # Count when Discord delivered the event, not after audit-log API latency.
        now = occurred_at if occurred_at is not None else time.monotonic()
        tracker = self.trackers[action_type][(guild.id, actor.id)]
        tracker.append(now)

        while tracker and now - tracker[0] > config["time_window"]:
            tracker.popleft()

        last = self.last_triggered[(guild.id, actor.id)].get(action_type, 0)
        if len(tracker) >= config["limit"] and now - last >= config["time_window"]:
            self.last_triggered[(guild.id, actor.id)][action_type] = now
            await self.apply_punishment(guild, actor, config["punishment"], action_type)

    async def apply_punishment(self, guild: disnake.Guild, actor, punishment: str, action_type: str):
        if actor is None or (guild.me and actor.id == guild.me.id):
            return
        if actor.id == guild.owner_id:
            await self.log_raid(guild, action_type, actor, "пропущено: владелец сервера")
            return

        if not AUTO_PUNISH:
            await self.log_raid(
                guild, action_type, actor,
                "только журналирование (ANTIRAID_AUTO_PUNISH=false)"
            )
            return

        reason = f"Анти-рейд: превышен порог для действия «{action_type}»"
        member = actor if isinstance(actor, disnake.Member) else guild.get_member(actor.id)
        if member is None:
            try:
                member = await guild.fetch_member(actor.id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                member = None

        if punishment in {"kick", "clear_roles_kick"}:
            if member is None:
                await self.log_raid(guild, action_type, actor, "требуется кик, но участник уже вышел или не найден")
                return
            try:
                await member.kick(reason=reason)
                await self.log_raid(guild, action_type, member, "кик выполнен")
            except (disnake.Forbidden, disnake.HTTPException) as exc:
                await self.log_raid(
                    guild, action_type, member,
                    f"НЕ УДАЛОСЬ КИКНУТЬ: {type(exc).__name__}; проверь права Kick Members и иерархию ролей"
                )
            return

        if punishment == "timeout_3h":
            if member is None:
                await self.log_raid(guild, action_type, actor, "таймаут не выдан: участник не найден")
                return
            try:
                until = disnake.utils.utcnow() + datetime_module.timedelta(hours=3)
                await member.timeout(until, reason=reason)
                await self.log_raid(guild, action_type, member, "таймаут 3 часа выполнен")
            except (disnake.Forbidden, disnake.HTTPException) as exc:
                await self.log_raid(
                    guild, action_type, member,
                    f"НЕ УДАЛОСЬ ВЫДАТЬ ТАЙМАУТ: {type(exc).__name__}; проверь права и иерархию ролей"
                )
            return

        await self.log_raid(guild, action_type, actor, f"неизвестный тип наказания: {punishment}")

    async def log_raid(self, guild: disnake.Guild, action_type: str, actor, punishment: str):
        channel = guild.system_channel or next(iter(guild.text_channels), None)
        if channel:
            embed = disnake.Embed(
                title="🚨 Сработала анти-рейд система!",
                description=f"**Действие:** {action_type}\n"
                            f"**Нарушитель:** {actor.mention if hasattr(actor, 'mention') else str(actor)}\n"
                            f"**Наказание:** {punishment}",
                color=disnake.Color.red(),
                timestamp=disnake.utils.utcnow()
            )
            try:
                await channel.send(embed=embed)
            except (disnake.Forbidden, disnake.HTTPException):
                # A missing log-channel permission must not crash anti-raid handling.
                pass

    # ---------- БЭКАП СЕРВЕРА ----------
    @commands.slash_command(name="бэкап", description="📦 Создать бэкап структуры сервера")
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

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        await inter.edit_original_response(content=f"✅ Бэкап сервера сохранён: `{filename}`")

    # ---------- ВОССТАНОВЛЕНИЕ ИЗ БЭКАПА ----------
    @commands.slash_command(name="восстановить_бэкап", description="🔄 Восстановить структуру сервера из бэкапа")
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

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data["id_сервера"] != guild.id:
            await inter.edit_original_response("❌ Этот бэкап не принадлежит текущему серверу.")
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
    async def set_config(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тип: str = commands.Param(choices=["создание_каналов", "изменение_каналов", "удаление_каналов",
                                           "создание_ролей", "изменение_ролей", "удаление_ролей", "бан", "спам"]),
        лимит: int = commands.Param(description="Количество действий до срабатывания (0 = выкл)"),
        окно: int = commands.Param(description="Временное окно в секундах"),
        наказание: str = commands.Param(choices=["очистка_ролей_кик", "таймаут_3ч"])
    ):
        punishment_map = {
            "очистка_ролей_кик": "clear_roles_kick",
            "таймаут_3ч": "timeout_3h"
        }
        self.config[тип] = {"limit": лимит, "time_window": окно, "punishment": punishment_map[наказание]}
        await inter.response.send_message(
            f"✅ Настройки для **{тип}** обновлены:\n"
            f"Лимит: {лимит}\nОкно: {окно} сек\nНаказание: {наказание}",
            ephemeral=True
        )

    @antiraid.sub_command(name="статус", description="Показать текущие настройки анти-рейда")
    async def show_config(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="🛡️ Настройки анти-рейда", color=disnake.Color.blurple())
        for action, cfg in self.config.items():
            status = "✅ Вкл" if cfg["limit"] > 0 else "❌ Выкл"
            punishment_map = {
                "clear_roles_kick": "очистка_ролей + кик",
                "timeout_3h": "таймаут 3 часа"
            }
            embed.add_field(
                name=action.replace("_", " ").capitalize(),
                value=f"Лимит: {cfg['limit']}\nОкно: {cfg['time_window']}с\nНаказание: {punishment_map.get(cfg['punishment'], cfg['punishment'])}",
                inline=True
            )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @antiraid.sub_command(name="сброс", description="Сбросить все настройки к значениям по умолчанию")
    async def reset_config(self, inter: disnake.ApplicationCommandInteraction):
        self.config = RAID_CONFIG.copy()
        await inter.response.send_message("✅ Настройки анти-рейда сброшены до значений по умолчанию.", ephemeral=True)

def setup(bot: commands.InteractionBot):
    bot.add_cog(AntiRaid(bot))