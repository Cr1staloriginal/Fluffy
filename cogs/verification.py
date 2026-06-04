import disnake
from disnake import ui
from disnake.ext import commands
import os

SUBMIT_CHANNEL_ID = int(os.getenv("VERIFICATION_CHANNEL_ID", 0))

class AnketaModal(ui.Modal):
    def __init__(self, submit_channel_id: int):
        super().__init__(title="Отвечай честно и с большим шансом попадёшь к нам")
        self.submit_channel_id = submit_channel_id
        self.add_item(ui.TextInput(
            label="Как вы узнали о нашем сервере?",
            style=disnake.TextInputStyle.short,
            placeholder="Через рекламу, друга, партнёрство или другое",
            required=True,
            max_length=200
        ))
        self.add_item(ui.TextInput(
            label='Что для вас лично означает "фурри-фэндом"?',
            style=disnake.TextInputStyle.paragraph,
            required=True,
            max_length=1000
        ))
        self.add_item(ui.TextInput(
            label="Вас начнут оскорблять в чате, ваши действия?",
            style=disnake.TextInputStyle.paragraph,
            required=True,
            max_length=500
        ))
        self.add_item(ui.TextInput(
            label="Есть ли у вас фурсона? Если есть, расскажите",
            style=disnake.TextInputStyle.paragraph,
            required=False,
            max_length=4000
        ))
        self.add_item(ui.TextInput(
            label="Ознакомились ли вы с правилами сервера?",
            style=disnake.TextInputStyle.short,
            required=True,
            placeholder="Да / Нет",
            max_length=100
        ))

    async def on_submit(self, interaction: disnake.ModalInteraction):
        answers = [item.value.strip() or "Нет ответа" for item in self.children]
        submit_channel = interaction.bot.get_channel(self.submit_channel_id)
        if not submit_channel:
            await interaction.response.send_message("Ошибка: канал для заявок не найден.", ephemeral=True)
            return
        embed = disnake.Embed(title="Новая заявка", color=0xffb347, timestamp=disnake.utils.utcnow())
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Основная информация", value=f"{interaction.user.mention} | {interaction.user}", inline=False)
        questions = [
            "Как вы узнали о нашем сервере?",
            'Что для вас лично означает "фурри-фэндом"?',
            "Вас начнут оскорблять в чате, ваши действия?",
            "Есть ли у вас фурсона? Если есть расскажи",
            "Ознакомились ли вы с правилами сервера?"
        ]
        for q, a in zip(questions, answers):
            embed.add_field(name=q, value=a[:1024], inline=False)
        try:
            await submit_channel.send(embed=embed)
        except Exception as e:
            print(f"AnketaModal: не удалось отправить заявку в канал {self.submit_channel_id}: {e}")
            try:
                await interaction.response.send_message("Ошибка: не удалось отправить вашу заявку. Пожалуйста, свяжитесь с модерацией.", ephemeral=True)
            except Exception:
                pass
            return
        try:
            await interaction.response.send_message("Спасибо! Анкета отправлена.", ephemeral=True)
        except Exception:
            pass

class AnketaView(ui.View):
    def __init__(self, submit_channel_id: int):
        super().__init__(timeout=None)
        self.submit_channel_id = submit_channel_id

    @ui.button(label="Заявка", style=disnake.ButtonStyle.blurple, custom_id="anketa:submit_button")
    async def anketa_button(self, interaction: disnake.MessageInteraction, button: ui.Button):
        await interaction.response.send_modal(AnketaModal(self.submit_channel_id))

class AnketaCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.submit_channel_id = SUBMIT_CHANNEL_ID or 0

    @commands.slash_command(
        name="setup_anketa",
        description="📝 Отправить кнопку анкеты в канал верификации",
        default_member_permissions=disnake.Permissions.administrator.value
    )
    @commands.has_permissions(administrator=True)
    async def setup_anketa(self, inter: disnake.ApplicationCommandInteraction):
        if not self.submit_channel_id:
            await inter.response.send_message("❌ VERIFICATION_CHANNEL_ID не установлен в .env", ephemeral=True)
            return
        
        channel = disnake.utils.get(inter.guild.text_channels, name="📝╔верификация")
        if not channel:
            await inter.response.send_message("Не найден канал '📝╔верификация'.", ephemeral=True)
            return
        embed = disnake.Embed(title="Добро пожаловать!", description="Нажмите кнопку для подачи заявки.", color=0x00ff88)
        try:
            await channel.send(embed=embed, view=AnketaView(self.submit_channel_id))
            await inter.response.send_message(f"✅ Отправлено в {channel.mention}", ephemeral=True)
        except Exception as e:
            print(f"AnketaCog: не удалось отправить сообщение в канал {getattr(channel,'id',channel)}: {e}")
            await inter.response.send_message("❌ Не удалось опубликовать кнопку анкеты в указанный канал.", ephemeral=True)

    def cog_load(self):
        try:
            self.bot.add_view(AnketaView(self.submit_channel_id))
        except Exception as e:
            print(f"AnketaCog: не удалось добавить view при загрузке: {e}")

def setup(bot: commands.InteractionBot):
    bot.add_cog(AnketaCog(bot))
