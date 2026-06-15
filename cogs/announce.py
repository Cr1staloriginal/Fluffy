import disnake
from disnake.ext import commands
from utils.colors import main_color

class AnnounceModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Заголовок",
                placeholder="Введите заголовок объявления",
                custom_id="announce_title",
                required=True,
                max_length=256
            ),
            disnake.ui.TextInput(
                label="Текст объявления",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Поддерживает Markdown: **жирный**, *курсив*, [ссылки](https://example.com)",
                custom_id="announce_text",
                required=True,
                max_length=2000
            ),
            disnake.ui.TextInput(
                label="Цвет (опционально)",
                placeholder="голубой, зелёный, красный, жёлтый, фиолетовый, оранжевый",
                custom_id="announce_color",
                required=False,
                max_length=20
            ),
            disnake.ui.TextInput(
                label="Ссылка на картинку (опционально)",
                placeholder="https://example.com/image.png",
                custom_id="announce_image",
                required=False,
                max_length=500
            )
        ]
        super().__init__(title="📢 Создание объявления", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        title = inter.text_values.get("announce_title", "Без заголовка")
        text = inter.text_values.get("announce_text", "")
        color_name = inter.text_values.get("announce_color", "").lower().strip()
        image_url = inter.text_values.get("announce_image", "").strip()

        # Определяем цвет
        color_map = {
            "синий": disnake.Color.blue(),
            "зелёный": disnake.Color.green(),
            "красный": disnake.Color.red(),
            "жёлтый": disnake.Color.gold(),
            "фиолетовый": disnake.Color.purple(),
            "оранжевый": disnake.Color.orange(),
            "голубой": main_color()
        }
        color = color_map.get(color_name, main_color())

        embed = disnake.Embed(
            title=title,
            description=text,
            color=color,
            timestamp=disnake.utils.utcnow()
        )
        if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
            embed.set_image(url=image_url)
        embed.set_footer(text=f"Объявление | {inter.author.display_name}")

        await inter.response.send_message(embed=embed)

class Announce(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="объявление", description="📢 Создать объявление через модальное окно (только для администраторов)")
    @commands.has_permissions(administrator=True)
    async def announce(self, inter: disnake.ApplicationCommandInteraction):
        """Открывает модальное окно для создания объявления."""
        await inter.response.send_modal(AnnounceModal())

def setup(bot: commands.InteractionBot):
    bot.add_cog(Announce(bot))