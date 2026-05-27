import disnake
from disnake.ext import commands
from database import log_event

class VoiceLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if before.channel == after.channel:
            return

        embed = disnake.Embed(title="🎤 Голосовой канал", timestamp=disnake.utils.utcnow())
        if before.channel is None:
            embed.description = f"{member.mention} подключился к **{after.channel.name}**"
            embed.color = disnake.Color.green()
        elif after.channel is None:
            embed.description = f"{member.mention} отключился от **{before.channel.name}**"
            embed.color = disnake.Color.red()
        else:
            embed.description = f"{member.mention} переместился из **{before.channel.name}** → **{after.channel.name}**"
            embed.color = disnake.Color.gold()

        await self.bot.log_dispatcher.send("voice", embed)
        await log_event("voice_update", f"{member.id}|{before.channel.id if before.channel else None}->{after.channel.id if after.channel else None}")

def setup(bot: commands.Bot):
    bot.add_cog(VoiceLogs(bot))