from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Wydarzenia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='event', description='Informacja o evencie (admin).')
    async def event(self, interaction: app_commands.Context):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        await interaction.response.send_message('Brak aktywnych eventów.', ephemeral=True)

async def setup(bot):
    await bot.add_cog(Wydarzenia(bot))
