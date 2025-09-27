import discord, random, time, asyncio
from discord.ext import commands, tasks
from discord import app_commands
from .utils import read_db, write_db, channel_check

class Wydarzenia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot = bot
        self.event_task = tasks.loop(minutes=15)(self.random_event_check)
        self.event_task.start()

    async def random_event_check(self):
        db = await read_db()
        # small chance to trigger event
        roll = random.randint(1,1000)
        if roll <= 6 and not db.get('events',{}).get('active'):
            choice = random.choice(['Kraken','Skarb Posejdona','Festiwal Syren'])
            duration = 2*3600
            active = {'type': choice, 'until': int(time.time())+duration}
            db['events']['active'] = active
            # apply modifiers
            if choice == 'Kraken':
                db['events']['current_mods'] = {'pojedynek_rep_mult':2, 'explore_risk':+20}
            elif choice == 'Skarb Posejdona':
                db['events']['current_mods'] = {'explore_bonus':30}
            else:
                db['events']['current_mods'] = {'rp_bonus':2}
            await write_db(db)
        # expire
        if db.get('events',{}).get('active') and time.time() > db['events']['active']['until']:
            db['events']['active'] = None
            db['events']['current_mods'] = {}
            await write_db(db)

    @app_commands.command(name='status_wydarzenia', description='Pokaż aktywne wydarzenie.')
    async def status(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        ev = db.get('events',{}).get('active')
        await interaction.response.send_message(f'Aktualne wydarzenie: {ev}')

async def setup(bot):
    await bot.add_cog(Wydarzenia(bot))
