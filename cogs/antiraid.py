import disnake
from disnake.ext import commands, tasks
import time
import json
import os
from collections import deque, defaultdict
from datetime import datetime
import aiosqlite
from database import DB_PATH

# ---------------------- КОНФИГУРАЦИЯ ----------------------
RAID_CONFIG = {
    "channel_create": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "channel_edit": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "channel_delete": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "role_create": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "role_edit": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "role_delete": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "ban": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "spam": {"limit": 10, "time_window": 5, "punishment": "timeout_3h"}
}

# ---------------------- ОСНОВНОЙ КОГ ----------------------
class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.config = RAID_CONFIG.copy()
        self.trackers = {
            "channel_create": defaultdict(deque),
            "channel_edit": defaultdict(deque),
            "channel_delete": defaultdict(deque),
            "role_create": defaultdict(deque),
            "role_edit": defaultdict(deque),
            "role_delete": defaultdict(deque),
            "ban": defaultdict(deque),
            "spam": defaultdict(deque),
        }
        self.raid_active = False
        self.backup_channel_id = None  # ID канала для бэкапов

    # ---------- ОБРАБОТЧИКИ СОБЫТИЙ ----------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        await self.handle_action("channel_create", channel.guild, channel.guild.me)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        await self.handle_action("channel_edit", after.guild, after.guild.me)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        await self.handle_action("channel_delete", channel.guild, channel.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        await self.handle_action("role_create", role.guild, role.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        await self.handle_action("role_edit", after.guild, after.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        await self.handle_action("role_delete", role.guild, role.guild.me)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        await self.handle_action("ban", guild, guild.me)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return
        await self.handle_action("spam", message.guild, message.author)

    # ---------- ОСНОВНАЯ ЛОГИКА ----------
    async def handle_action(self, action_type: str, guild: disnake.Guild, actor):
        config = self.config.get(action_type)
        if not config or config.get("limit", 0) == 0:
            return

        now = time.time()
        tracker = self.trackers[action_type][guild.id]
        tracker.append(now)

        # Очищаем старые записи
        while tracker and now - tracker[0] > config["time_window"]:
            tracker.popleft()

        # Проверяем превышение лимита
        if len(tracker) >= config["limit"]:
            # Применяем наказание
            await self.apply_punishment(guild, actor, config["punishment"], action_type)

    async def apply_punishment(self, guild: disnake.Guild, actor, punishment: str, action_type: str):
        """Применяет наказание в зависимости от типа."""
        if punishment == "clear_roles_kick":
            # Очистка ролей у актора (если это участник) и кик
            if isinstance(actor, disnake.Member):
                try:
                    # Удаляем все роли (кроме @everyone)
                    await actor.edit(roles=[], reason=f"Анти-рейд: {action_type}")
                    # Кикаем
                    await actor.kick(reason=f"Анти-рейд: {action_type}")
                except:
                    pass
            elif isinstance(actor, disnake.User):
                # Если актор — пользователь (не на сервере), пробуем забанить
                try:
                    await guild.ban(actor, reason=f"Анти-рейд: {action_type}")
                except:
                    pass

            # Если это бот — кикаем
            if actor == guild.me:
                try:
                    await guild.leave()
                except:
                    pass

        elif punishment == "timeout_3h":
            if isinstance(actor, disnake.Member):
                try:
                    # Тайм-аут на 3 часа
                    until = disnake.utils.utcnow() + disnake.utils.timedelta(hours=3)
                    await actor.timeout(until, reason=f"Анти-рейд: спам")
                except:
                    pass

        # Логируем в канал
        await self.log_raid(guild, action_type, actor, punishment)

    # ---------- ЛОГИРОВАНИЕ ----------
    async def log_raid(self, guild: disnake.Guild, action_type: str, actor, punishment: str):
        channel = guild.system_channel or guild.text_channels[0]
        if channel:
            embed = disnake.Embed(
                title="🚨 Сработала анти-рейд система!",
                description=f"**Действие:** {action_type}\n"
                            f"**Нарушитель:** {actor.mention if hasattr(actor, 'mention') else str(actor)}\n"
                            f"**Наказание:** {punishment}",
                color=disnake.Color.red(),
                timestamp=disnake.utils.utcnow()
            )
            await channel.send(embed=embed)

    # ---------- БЭКАП СЕРВЕРА ----------
    @commands.slash_command(name="бэкап", description="📦 Создать бэкап структуры сервера")
    @commands.has_permissions(administrator=True)
    async def backup(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        guild = inter.guild
        data = {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "created_at": datetime.now().isoformat(),
            "categories": [],
            "channels": [],
            "roles": []
        }

        # Категории и каналы
        for category in guild.categories:
            cat_data = {
                "name": category.name,
                "position": category.position,
                "id": category.id
            }
            data["categories"].append(cat_data)

        for channel in guild.channels:
            if isinstance(channel, disnake.TextChannel):
                ch_data = {
                    "type": "text",
                    "name": channel.name,
                    "position": channel.position,
                    "topic": channel.topic,
                    "slowmode_delay": channel.slowmode_delay,
                    "category_id": channel.category_id,
                    "id": channel.id
                }
                data["channels"].append(ch_data)
            elif isinstance(channel, disnake.VoiceChannel):
                ch_data = {
                    "type": "voice",
                    "name": channel.name,
                    "position": channel.position,
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit,
                    "category_id": channel.category_id,
                    "id": channel.id
                }
                data["channels"].append(ch_data)

        # Роли (исключаем @everyone)
        for role in guild.roles:
            if role.name == "@everyone":
                continue
            role_data = {
                "name": role.name,
                "color": role.color.value,
                "permissions": role.permissions.value,
                "position": role.position,
                "mentionable": role.mentionable,
                "hoist": role.hoist,
                "id": role.id
            }
            data["roles"].append(role_data)

        # Сохраняем в JSON
        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        filename = f"backup_{guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        await inter.edit_original_response(f"✅ Бэкап сервера сохранён: `{filename}`")

    # ---------- ВОССТАНОВЛЕНИЕ ИЗ БЭКАПА ----------
    @commands.slash_command(name="восстановить_бэкап", description="🔄 Восстановить структуру сервера из бэкапа")
    @commands.has_permissions(administrator=True)
    async def restore_backup(self, inter: disnake.ApplicationCommandInteraction, имя_файла: str):
        await inter.response.defer()
        guild = inter.guild

        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        filepath = os.path.join(backup_dir, имя_файла)

        if not os.path.exists(filepath):
            await inter.edit_original_response("❌ Файл бэкапа не найден.")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Восстанавливаем роли (создаём новые, так как ID не совпадают)
        for role_data in data["roles"]:
            try:
                await guild.create_role(
                    name=role_data["name"],
                    color=disnake.Color(role_data["color"]),
                    permissions=disnake.Permissions(role_data["permissions"]),
                    mentionable=role_data["mentionable"],
                    hoist=role_data["hoist"]
                )
            except:
                pass

        # Восстанавливаем категории
        for cat_data in data["categories"]:
            try:
                await guild.create_category(name=cat_data["name"], position=cat_data["position"])
            except:
                pass

        # Восстанавливаем каналы (нужно сначала создать категории, но мы упростим)
        for ch_data in data["channels"]:
            try:
                if ch_data["type"] == "text":
                    await guild.create_text_channel(
                        name=ch_data["name"],
                        position=ch_data["position"],
                        topic=ch_data.get("topic", ""),
                        slowmode_delay=ch_data.get("slowmode_delay", 0)
                    )
                elif ch_data["type"] == "voice":
                    await guild.create_voice_channel(
                        name=ch_data["name"],
                        position=ch_data["position"],
                        bitrate=ch_data.get("bitrate", 64000),
                        user_limit=ch_data.get("user_limit", 0)
                    )
            except:
                pass

        await inter.edit_original_response("✅ Бэкап успешно восстановлен!")

    # ---------- НАСТРОЙКА КОНФИГА ----------
    @commands.slash_command(name="антирейд", description="🛡️ Настройка анти-рейд системы")
    @commands.has_permissions(administrator=True)
    async def antiraid(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @antiraid.sub_command(name="настроить", description="Изменить настройки анти-рейда")
    async def set_config(
        self,
        inter: disnake.ApplicationCommandInteraction,
        тип: str = commands.Param(choices=["channel_create", "channel_edit", "channel_delete",
                                           "role_create", "role_edit", "role_delete", "ban", "spam"]),
        лимит: int = commands.Param(description="Количество действий до срабатывания (0 = выкл)"),
        окно: int = commands.Param(description="Временное окно в секундах"),
        наказание: str = commands.Param(choices=["clear_roles_kick", "timeout_3h"])
    ):
        self.config[тип] = {"limit": лимит, "time_window": окно, "punishment": наказание}
        await inter.response.send_message(
            f"✅ Настройки для `{тип}` обновлены:\n"
            f"Лимит: {лимит}\nОкно: {окно} сек\nНаказание: {наказание}",
            ephemeral=True
        )

    @antiraid.sub_command(name="статус", description="Показать текущие настройки анти-рейда")
    async def show_config(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="🛡️ Настройки анти-рейда", color=disnake.Color.blurple())
        for action, cfg in self.config.items():
            status = "✅ Вкл" if cfg["limit"] > 0 else "❌ Выкл"
            embed.add_field(
                name=action.replace("_", " ").capitalize(),
                value=f"Лимит: {cfg['limit']}\nОкно: {cfg['time_window']}с\nНаказание: {cfg['punishment']}",
                inline=True
            )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @antiraid.sub_command(name="сброс", description="Сбросить все настройки к значениям по умолчанию")
    async def reset_config(self, inter: disnake.ApplicationCommandInteraction):
        self.config = RAID_CONFIG.copy()
        await inter.response.send_message("✅ Настройки анти-рейда сброшены до значений по умолчанию.", ephemeral=True)

def setup(bot: commands.InteractionBot):
    bot.add_cog(AntiRaid(bot))