from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

SHOP = {
    'mikstura': 200,
    'miecz': 500,
    'zbroja': 400
}

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='shop', description='Pokaż sklep.')
    async def shop(self, interaction: app_commands.Context):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        desc = '\n'.join([f"{k}: {v} KA" for k,v in SHOP.items()])
        await interaction.response.send_message(embed=discord.Embed(title='🛒 Sklep', description=desc), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
