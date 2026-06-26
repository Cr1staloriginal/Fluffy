import disnake
from disnake.ext import commands, tasks
import time
import json
import os
from collections import deque, defaultdict
from datetime import datetime
import aiosqlite
from database import DB_PATH

# ---------------------- КОНФИГУРАЦИЯ (на русском) ----------------------
RAID_CONFIG = {
    "создание_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "изменение_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
    "удаление_каналов": {"limit": 5, "time_window": 10, "punishment": "clear_roles_kick"},
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

    # ---------- ОБРАБОТЧИКИ СОБЫТИЙ ----------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        await self.handle_action("создание_каналов", channel.guild, channel.guild.me)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        await self.handle_action("изменение_каналов", after.guild, after.guild.me)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        await self.handle_action("удаление_каналов", channel.guild, channel.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: disnake.Role):
        await self.handle_action("создание_ролей", role.guild, role.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        await self.handle_action("изменение_ролей", after.guild, after.guild.me)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        await self.handle_action("удаление_ролей", role.guild, role.guild.me)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.User):
        await self.handle_action("бан", guild, guild.me)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return
        await self.handle_action("спам", message.guild, message.author)

    # ---------- ОСНОВНАЯ ЛОГИКА ----------
    async def handle_action(self, action_type: str, guild: disnake.Guild, actor):
        config = self.config.get(action_type)
        if not config or config.get("limit", 0) == 0:
            return

        now = time.time()
        tracker = self.trackers[action_type][guild.id]
        tracker.append(now)

        while tracker and now - tracker[0] > config["time_window"]:
            tracker.popleft()

        if len(tracker) >= config["limit"]:
            await self.apply_punishment(guild, actor, config["punishment"], action_type)

    async def apply_punishment(self, guild: disnake.Guild, actor, punishment: str, action_type: str):
        if punishment == "clear_roles_kick":
            if isinstance(actor, disnake.Member):
                try:
                    await actor.edit(roles=[], reason=f"Анти-рейд: {action_type}")
                    await actor.kick(reason=f"Анти-рейд: {action_type}")
                except:
                    pass
            elif isinstance(actor, disnake.User):
                try:
                    await guild.ban(actor, reason=f"Анти-рейд: {action_type}")
                except:
                    pass

            if actor == guild.me:
                try:
                    await guild.leave()
                except:
                    pass

        elif punishment == "timeout_3h":
            if isinstance(actor, disnake.Member):
                try:
                    until = disnake.utils.utcnow() + disnake.utils.timedelta(hours=3)
                    await actor.timeout(until, reason="Анти-рейд: спам")
                except:
                    pass

        await self.log_raid(guild, action_type, actor, punishment)

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
    async def restore_backup(self, inter: disnake.ApplicationCommandInteraction, имя_файла: str):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild

        backup_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
        filepath = os.path.join(backup_dir, имя_файла)

        if not os.path.exists(filepath):
            await inter.edit_original_response("❌ Файл бэкапа не найден.")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

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

        for cat_data in data["категории"]:
            try:
                await guild.create_category(name=cat_data["название"], position=cat_data["позиция"])
            except:
                pass

        for ch_data in data["каналы"]:
            try:
                if ch_data["тип"] == "текстовый":
                    await guild.create_text_channel(
                        name=ch_data["название"],
                        position=ch_data["позиция"],
                        topic=ch_data.get("тема", ""),
                        slowmode_delay=ch_data.get("задержка", 0)
                    )
                elif ch_data["тип"] == "голосовой":
                    await guild.create_voice_channel(
                        name=ch_data["название"],
                        position=ch_data["позиция"],
                        bitrate=ch_data.get("битрейт", 64000),
                        user_limit=ch_data.get("лимит", 0)
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
                "clear_roles_kick": "очистка ролей + кик",
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