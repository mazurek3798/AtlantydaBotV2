from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Gildie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='gildia', description='Pokaż informacje o swojej gildii.')
    async def gildia(self, interaction: app_commands.Context):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db(); uid = str(interaction.user.id); ensure_user(db, uid)
        u = db['users'][uid]
        guild = u.get('guild')
        if not guild:
            await interaction.response.send_message('Nie jesteś w gildii.', ephemeral=True); return
        await interaction.response.send_message(f'Gildia: {guild}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(Gildie(bot))
