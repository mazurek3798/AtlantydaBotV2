import discord, random, time
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check

class Pojedynki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='pojedynek', description='Wyzwanie do pojedynku.')
    async def pojedynek(self, interaction: discord.Interaction, target: discord.Member, stawka: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True)
            return
        if target.bot:
            await interaction.response.send_message('Nie możesz walczyć z botem.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id); tid = str(target.id)
        ensure_user(db, uid); ensure_user(db, tid)
        a = db['users'][uid]; b = db['users'][tid]
        if stawka <=0:
            await interaction.response.send_message('Stawka musi być > 0', ephemeral=True); return
        if stawka > a['ka']*0.5 or stawka > b['ka']*0.5:
            await interaction.response.send_message('Stawka nie może przekraczać 50% salda któregokolwiek gracza.', ephemeral=True); return
        view = ui.View(timeout=60)
        accepted = {'value': False}
        @ui.button(label='Akceptuj', style=discord.ButtonStyle.green)
        async def accept(i: Interaction, button: ui.Button):
            if i.user.id != target.id:
                await i.response.send_message('Tylko wyzwany może akceptować.', ephemeral=True); return
            accepted['value'] = True
            view.stop()
            await i.response.edit_message(content='Wyzwanie zaakceptowane. Rozpoczynam pojedynek...', view=None)
        @ui.button(label='Odrzuć', style=discord.ButtonStyle.red)
        async def reject(i: Interaction, button: ui.Button):
            if i.user.id != target.id:
                await i.response.send_message('Tylko wyzwany może odrzucić.', ephemeral=True); return
            accepted['value'] = False; view.stop()
            await i.response.edit_message(content='Wyzwanie odrzucone.', view=None)
        await interaction.response.send_message(f'{target.mention}, {interaction.user.mention} wyzywa Cię na pojedynek o {stawka} KA. Akceptujesz?', view=view)
        await view.wait()
        if not accepted['value']:
            return
        # compute win chance based on level and items
        chance = 50 + (a.get('level',0)-b.get('level',0))*5
        if 'trojzab' in a.get('items',{}):
            chance += 12
        if 'trojzab' in b.get('items',{}):
            chance -= 12
        roll = random.randint(1,100)
        if roll <= chance:
            # a wins
            a['ka'] += stawka
            b['ka'] -= stawka
            a['earned_total'] += stawka
            b['spent_total'] += stawka
            a['reputation'] += 2
            b['reputation'] -= 1
            a['badges'] = list(set(a.get('badges',[])+['Mistrz Pojedynków']))
            result = f'{interaction.user.mention} wygrywa i zdobywa {stawka} KA!'
        else:
            b['ka'] += stawka
            a['ka'] -= stawka
            b['earned_total'] += stawka
            a['spent_total'] += stawka
            b['reputation'] += 2
            a['reputation'] -= 1
            b['badges'] = list(set(b.get('badges',[])+['Mistrz Pojedynków']))
            result = f'{target.mention} wygrywa i zdobywa {stawka} KA!'
        # level update and anti-cheat floor
        a['ka'] = max(0, a['ka']); b['ka'] = max(0, b['ka'])
        a['level'] = (a.get('earned_total',0)+a.get('spent_total',0))//1000
        b['level'] = (b.get('earned_total',0)+b.get('spent_total',0))//1000
        await write_db(db)
        await interaction.followup.send(result)

async def setup(bot):
    await bot.add_cog(Pojedynki(bot))
