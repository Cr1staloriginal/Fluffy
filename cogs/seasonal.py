import disnake
from disnake.ext import commands
import aiosqlite
from pathlib import Path
from database import (
    DB_PATH,
    load_seasonal_phrases_from_file,
    clear_phrases_by_season
)
from utils.seasons import (
    get_current_season,
    get_season_name,
    get_season_end_date,
    get_all_seasons
)


class Seasonal(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="сезон", description="🎭 Управление сезонными фразами (только для владельца)")
    @commands.is_owner()
    async def seasonal(self, inter: disnake.ApplicationCommandInteraction):
        """Группа команд для управления сезонными фразами."""
        pass

    @seasonal.sub_command(name="статус", description="Показать текущий сезон и количество фраз")
    async def status(self, inter: disnake.ApplicationCommandInteraction):
        season = get_current_season()

        async with aiosqlite.connect(str(DB_PATH)) as db:
            async with db.execute(
                "SELECT season, COUNT(*) FROM phrases GROUP BY season"
            ) as cur:
                rows = await cur.fetchall()

        embed = disnake.Embed(
            title="🎭 Сезонные фразы",
            description=(
                f"**Текущий сезон:** {get_season_name(season)}\n"
                f"**Период:** {get_season_end_date(season)}"
            ),
            color=disnake.Color.orange(),
            timestamp=disnake.utils.utcnow()
        )

        if rows:
            for s, count in rows:
                embed.add_field(
                    name=get_season_name(s),
                    value=f"**{count}** фраз",
                    inline=True
                )
        else:
            embed.add_field(name="Фразы", value="База пуста", inline=False)

        await inter.response.send_message(embed=embed, ephemeral=True)

    @seasonal.sub_command(name="загрузить", description="Загрузить сезонные фразы из файла")
    async def load(
        self,
        inter: disnake.ApplicationCommandInteraction,
        сезон: str = commands.Param(
            choices=["halloween", "new_year", "valentine", "spring", "easter", "server_birthday"],
            description="Какой сезон загрузить"
        ),
        имя_файла: str = None
    ):
        """Загружает фразы из файла (например, halloween.txt)."""
        if имя_файла is None:
            имя_файла = f"{сезон}.txt"

        file_path = Path(__file__).parent.parent / имя_файла
        if not file_path.exists():
            await inter.response.send_message(
                f"❌ Файл `{имя_файла}` не найден в корне проекта.",
                ephemeral=True
            )
            return

        count = await load_seasonal_phrases_from_file(str(file_path), сезон)
        await inter.response.send_message(
            f"✅ Загружено **{count}** фраз для сезона {get_season_name(сезон)}.\n"
            f"Файл: `{имя_файла}`",
            ephemeral=True
        )

    @seasonal.sub_command(name="загрузить_все", description="Загрузить фразы для всех сезонов из файлов")
    async def load_all(self, inter: disnake.ApplicationCommandInteraction):
        """Загружает фразы для всех сезонов из файлов в корне проекта."""
        await inter.response.defer(ephemeral=True)
        base_dir = Path(__file__).parent.parent
        total = 0
        results = []

        for season in get_all_seasons():
            file_path = base_dir / f"{season}.txt"
            if file_path.exists():
                count = await load_seasonal_phrases_from_file(str(file_path), season)
                total += count
                results.append(f"• {get_season_name(season)}: **{count}** фраз")
            else:
                results.append(f"• {get_season_name(season)}: ❌ файл `{season}.txt` не найден")

        embed = disnake.Embed(
            title="📦 Загрузка сезонных фраз",
            description="\n".join(results) + f"\n\n**Всего загружено:** {total}",
            color=disnake.Color.green()
        )
        await inter.edit_original_response(embed=embed)

    @seasonal.sub_command(name="очистить", description="Удалить все фразы указанного сезона")
    async def clear(
        self,
        inter: disnake.ApplicationCommandInteraction,
        сезон: str = commands.Param(
            choices=["halloween", "new_year", "valentine", "spring", "easter", "server_birthday"],
            description="Какой сезон очистить"
        )
    ):
        await clear_phrases_by_season(сезон)
        await inter.response.send_message(
            f"🗑️ Все фразы сезона {get_season_name(сезон)} удалены.",
            ephemeral=True
        )

    @seasonal.sub_command(name="обновить_статус", description="Принудительно обновить статус бота")
    async def force_update(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        rotator = self.bot.get_cog("StatusRotator")
        if rotator:
            await rotator.update_status()
            await inter.edit_original_response(
                "✅ Статус обновлён принудительно. Смотри консоль, что именно поставлено."
            )
        else:
            await inter.edit_original_response("❌ Ког StatusRotator не найден.")


def setup(bot: commands.InteractionBot):
    bot.add_cog(Seasonal(bot))