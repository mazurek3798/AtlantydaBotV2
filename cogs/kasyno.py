import random
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_xp

class Kasyno(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='kasyno', description='Zagraj w kasynie. Wygrana = x2, przegrana = tracisz stawkę i -1 reputacji.')
    async def kasyno(self, interaction:  app_commands.Context, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        if kwota <= 0:
            await interaction.response.send_message('Kwota musi być > 0.', ephemeral=True); return
        db = await read_db(); uid = str(interaction.user.id)
        ensure_user(db, uid); user = db['users'][uid]
        if user.get('ka',0) < kwota:
            await interaction.response.send_message('Nie masz wystarczająco KA.', ephemeral=True); return
        win = random.choice([True, False])
        if win:
            user['ka'] += kwota
            user['earned_total'] += kwota
            user['xp'] = user.get('xp',0) + 10
            user['level'] = level_from_xp(user['xp'])
            await write_db(db)
            await interaction.response.send_message(f'🎉 Wygrałeś {kwota} KA! Masz teraz {user["ka"]} KA.')
        else:
            user['ka'] = max(0, user.get('ka',0) - kwota)
            user['spent_total'] = user.get('spent_total',0) + kwota
            user['reputation'] = max(0, user.get('reputation',0) - 1)
            await write_db(db)
            await interaction.response.send_message(f'💀 Przegrałeś {kwota} KA i -1 reputacji. Masz teraz {user["ka"]} KA.')

async def setup(bot):
    await bot.add_cog(Kasyno(bot))
