import discord, time, random
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Gildie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='utworz_gildie', description='Utwórz gildię (koszt 1000 KA).')
    async def utworz(self, interaction: discord.Interaction, nazwa: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        if user['ka'] < 1000:
            await interaction.response.send_message('Nie masz 1000 KA na utworzenie gildii.', ephemeral=True); return
        if nazwa in db['guilds_list']:
            await interaction.response.send_message('Gildia o takiej nazwie już istnieje.', ephemeral=True); return
        user['ka'] -= 1000
        db['guilds_list'][nazwa] = {
            'owner': uid,
            'members': [uid],
            'treasury': 0,
            'created': int(time.time()),
            'quests': {},
            'weekly_goal': None
        }
        await write_db(db)
        await interaction.response.send_message(f'Gildia {nazwa} została utworzona.')

    @app_commands.command(name='dolacz_gildia', description='Dołącz do gildii.')
    async def dolacz(self, interaction: discord.Interaction, nazwa: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Nie odnaleziono takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        if uid in g['members']:
            await interaction.response.send_message('Jesteś już w tej gildii.', ephemeral=True); return
        if len(g['members']) >= 20:
            await interaction.response.send_message('Gildia ma już limit 20 członków.', ephemeral=True); return
        g['members'].append(uid)
        await write_db(db)
        await interaction.response.send_message(f'Dołączyłeś do gildii {nazwa}.')

    @app_commands.command(name='wpłata', description='Wpłać KA do skarbca gildii.')
    async def wplata(self, interaction: discord.Interaction, nazwa: str, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Brak takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        if uid not in g['members']:
            await interaction.response.send_message('Musisz być członkiem gildii by wpłacać.', ephemeral=True); return
        if kwota <=0 or user['ka'] < kwota:
            await interaction.response.send_message('Niepoprawna kwota.', ephemeral=True); return
        user['ka'] -= kwota
        g['treasury'] += kwota
        user['spent_total'] += kwota
        await write_db(db)
        await interaction.response.send_message(f'Wpłacono {kwota} KA do skarbca gildii {nazwa}.')

    @app_commands.command(name='skarb_gildii', description='Pokaż skarbiec gildii.')
    async def skarbiec(self, interaction: discord.Interaction, nazwa: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Brak takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        await interaction.response.send_message(f'Skarbiec gildii {nazwa}: {g["treasury"]} KA. Członków: {len(g["members"])}/{20}')

    @app_commands.command(name='ranking_gildi', description='Pokaż ranking gildii wg skarbca.')
    async def ranking(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        items = sorted(db['guilds_list'].items(), key=lambda x: x[1].get('treasury',0), reverse=True)
        text = '\n'.join([f"{i+1}. {name} - {data.get('treasury',0)} KA" for i,(name,data) in enumerate(items[:10])])
        await interaction.response.send_message('Ranking gildii:\n'+(text or 'Brak gildii.'))

    @app_commands.command(name='gildyjne_quest', description='Stwórz tygodniowy quest gildii (tylko właściciel).')
    async def gildyjne_quest(self, interaction: discord.Interaction, nazwa: str, cel_kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Brak takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        uid = str(interaction.user.id)
        if g.get('owner') != uid:
            await interaction.response.send_message('Tylko właściciel gildii może ustawić quest.', ephemeral=True); return
        if cel_kwota <= 0:
            await interaction.response.send_message('Cel musi być większy niż 0.', ephemeral=True); return
        # set weekly goal (7 days)
        g['weekly_goal'] = {'target': cel_kwota, 'progress': 0, 'until': int(time.time()) + 7*24*3600, 'claimed': False}
        await write_db(db)
        await interaction.response.send_message(f'Ustawiono tygodniowy cel gildii: zebrać {cel_kwota} KA w skarbcu w 7 dni.')

    @app_commands.command(name='gildyjne_quest_status', description='Status tygodniowego celu gildii.')
    async def gildyjne_status(self, interaction: discord.Interaction, nazwa: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Brak takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        goal = g.get('weekly_goal')
        if not goal:
            await interaction.response.send_message('Brak aktywnego tygodniowego celu.', ephemeral=True); return
        await interaction.response.send_message(f'Target: {goal["target"]} KA\nProgress: {goal["progress"]} KA\nDo: <t:{goal["until"]}:R>\nZrealizowane: {goal.get("claimed",False)}')

    @app_commands.command(name='gildyjne_claim', description='Odbierz nagrodę za ukończenie celu gildii (właściciel).')
    async def gildyjne_claim(self, interaction: discord.Interaction, nazwa: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        if nazwa not in db['guilds_list']:
            await interaction.response.send_message('Brak takiej gildii.', ephemeral=True); return
        g = db['guilds_list'][nazwa]
        uid = str(interaction.user.id)
        if g.get('owner') != uid:
            await interaction.response.send_message('Tylko właściciel gildii może odebrać nagrodę.', ephemeral=True); return
        goal = g.get('weekly_goal')
        if not goal:
            await interaction.response.send_message('Brak aktywnego celu.', ephemeral=True); return
        if goal.get('claimed', False):
            await interaction.response.send_message('Nagroda już odebrana.', ephemeral=True); return
        if goal['progress'] >= goal['target']:
            # reward: split treasury by members as bonus 10% of target
            bonus = int(goal['target'] * 0.1)
            per_member = max(1, bonus // max(1, len(g['members'])))
            for m in g['members']:
                ensure_user(db, m)
                db['users'][m]['ka'] += per_member
                db['users'][m]['earned_total'] += per_member
            goal['claimed'] = True
            await write_db(db)
            await interaction.response.send_message(f'Nagroda przyznana: każdy członek otrzymuje {per_member} KA.')
        else:
            await interaction.response.send_message('Cel nie został osiągnięty, nie można odebrać nagrody.', ephemeral=True)

async def setup(bot):
    await bot.add_cog(Gildie(bot))
