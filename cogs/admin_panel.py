import discord, time, asyncio
from discord.ext import commands, tasks
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, channel_check

class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot = bot
        self.weekly_task = tasks.loop(seconds=24*3600)(self.daily_checks)  # daily checks; weekly report triggered by counter
        self.weekly_counter = 0
        self.weekly_task.start()

    async def daily_checks(self):
        # increment counter and on 7th day send weekly report
        self.weekly_counter += 1
        if self.weekly_counter >= 7:
            await self.send_weekly_report()
            self.weekly_counter = 0

    async def send_weekly_report(self):
        db = await read_db()
        users = db.get('users',{})
        top5 = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)[:5]
        text = '\n'.join([f"{idx+1}. <@{uid}> - {data.get('ka',0)} KA" for idx,(uid,data) in enumerate(top5)])
        for guild in self.bot.guilds:
            # try find channel named Atlantyda
            ch = discord.utils.get(guild.text_channels, name='Atlantyda')
            if ch:
                try:
                    await ch.send('Tygodniowy raport - top5 najbogatszych:\n' + (text or 'Brak danych.'))
                except Exception:
                    pass

    @app_commands.command(name='admin_panel', description='Panel admina (tylko dla administratorów).')
    async def admin_panel(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('Tylko administratorzy.', ephemeral=True); return
        view = ui.View(timeout=None)
        async def trigger_event(i: Interaction):
            db = await read_db()
            db['events']['active'] = {'type':'Festiwal Syren','until': int(time.time())+3600}
            db['events']['current_mods'] = {'rp_bonus':2}
            await write_db(db)
            await i.response.send_message('Aktywowałeś Festiwal Syren (1h).', ephemeral=True)
        async def season_reset(i: Interaction):
            db = await read_db()
            users = db.get('users',{})
            top = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)[:10]
            db['season']['top_this_season'] = [u for u,_ in top]
            db['season']['current'] = db['season'].get('current',1)+1
            db['season']['season_start'] = int(time.time())
            # distribute season badges to top 3
            for idx,(uid,_) in enumerate(top[:3]):
                ensure = users.get(uid)
                ensure['badges'] = list(set(ensure.get('badges',[])+[f'Sezon_{db["season"]["current"]}_Top{idx+1}']))
            await write_db(db)
            await i.response.send_message('Wykonano reset sezonu i nadano odznaki top 3.', ephemeral=True)
        async def report(i: Interaction):
            db = await read_db()
            users = db.get('users',{})
            top5 = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)[:5]
            text = '\n'.join([f"{idx+1}. <@{uid}> - {data.get('ka',0)} KA" for idx,(uid,data) in enumerate(top5)])
            await i.response.send_message('Raport admina (top5 najbogatszych):\n'+(text or 'Brak danych.'), ephemeral=True)
        btn_event = ui.Button(label='Aktywuj Festiwal Syren', style=discord.ButtonStyle.primary)
        btn_event.callback = trigger_event
        btn_season = ui.Button(label='Reset sezonu', style=discord.ButtonStyle.danger)
        btn_season.callback = season_reset
        btn_report = ui.Button(label='Raport admina', style=discord.ButtonStyle.secondary)
        btn_report.callback = report
        view.add_item(btn_event); view.add_item(btn_season); view.add_item(btn_report)
        await interaction.response.send_message('Panel admina:', view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminPanel(bot))
