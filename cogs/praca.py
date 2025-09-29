import random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_xp

class Praca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def do_work(self, user_id: int):
        db = await read_db()
        uid = str(user_id)
        ensure_user(db, uid)
        user = db['users'][uid]
        now = int(time.time())
        cooldown = 10*60
        if now - user.get('last_work',0) < cooldown:
            return None
        reward = random.randint(10,200)
        if random.randint(1,100) <= 12:
            user['items']['fragment'] = user['items'].get('fragment',0) + 1
        user['ka'] += reward
        user['earned_total'] += reward
        user['last_work'] = now
        user['xp'] = user.get('xp',0) + 5
        user['level'] = level_from_xp(user['xp'])
        await write_db(db)
        return reward

    @app_commands.command(name='praca', description='Wykonaj pracę (cooldown 10 min).')
    async def praca(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        res = await self.do_work(interaction.user.id)
        if res is None:
            db = await read_db(); uid = str(interaction.user.id)
            left = 10*60 - (int(time.time()) - db['users'][uid].get('last_work',0))
            await interaction.response.send_message(f'⏳ Możesz pracować za {left//60}m {left%60}s.', ephemeral=True)
            return
        await interaction.response.send_message(f'🛠️ Pracowałeś i zarobiłeś **{res} KA**!', ephemeral=False)

async def setup(bot):
    await bot.add_cog(Praca(bot))
