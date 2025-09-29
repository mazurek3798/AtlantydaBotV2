import random
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check, level_from_xp

class DuelView(ui.View):
    def __init__(self, challenger, target, amount):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.amount = amount

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id not in (self.target.id, self.challenger.id):
            await interaction.response.send_message('Nie możesz użyć tych przycisków.', ephemeral=True)
            return False
        return True

    @ui.button(label='⚔️ Akceptuj', style=discord.ButtonStyle.success)
    async def accept(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message('Tylko wyzwany może zaakceptować.', ephemeral=True); return
        await interaction.response.edit_message(content='Wyzwanie zaakceptowane. Rozpoczynam pojedynek...', view=None)
        await self.run_duel(interaction)

    @ui.button(label='❌ Odrzuć', style=discord.ButtonStyle.danger)
    async def reject(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message('Tylko wyzwany może odrzucić.', ephemeral=True); return
        await interaction.response.edit_message(content='Wyzwanie odrzucone.', view=None)

    async def run_duel(self, interaction: Interaction):
        db = await read_db()
        a_id = str(self.challenger.id); b_id = str(self.target.id)
        ensure_user(db, a_id); ensure_user(db, b_id)
        a = db['users'][a_id]; b = db['users'][b_id]
        if a.get('ka',0) < self.amount or b.get('ka',0) < self.amount:
            await interaction.followup.send('Któryś z graczy nie ma wystarczająco KA.', ephemeral=True); return
        a_hp = 100 + a.get('level',0)*10
        b_hp = 100 + b.get('level',0)*10
        a_atk = 10 + a.get('level',0)*2
        b_atk = 10 + b.get('level',0)*2
        turn = 0
        while a_hp > 0 and b_hp > 0:
            if turn % 2 == 0:
                b_hp -= random.randint(int(a_atk*0.6), int(a_atk*1.4))
            else:
                a_hp -= random.randint(int(b_atk*0.6), int(b_atk*1.4))
            turn += 1
        if a_hp > 0:
            winner, loser = a, b; winner_id, loser_id = a_id, b_id
        else:
            winner, loser = b, a; winner_id, loser_id = b_id, a_id
        winner['ka'] += self.amount; winner['earned_total'] += self.amount; winner['xp'] = winner.get('xp',0)+20
        loser['ka'] = max(0, loser.get('ka',0) - self.amount); loser['spent_total'] = loser.get('spent_total',0) + self.amount
        loser['reputation'] = max(0, loser.get('reputation',0) - 1)
        winner['badges'] = list(set(winner.get('badges',[]) + ['Mistrz Pojedynków']))
        winner['level'] = level_from_xp(winner.get('xp',0)); loser['level'] = level_from_xp(loser.get('xp',0))
        await write_db(db)
        await interaction.followup.send(f'🏆 <@{winner_id}> wygrał pojedynek i zdobywa {self.amount} KA!')

class Pojedynki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='pojedynek', description='Wyzwanie gracza do pojedynku.')
    async def pojedynek(self, interaction:  app_commands.Context, target: discord.Member, stawka: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        if target.bot:
            await interaction.response.send_message('Nie możesz walczyć z botem.', ephemeral=True); return
        db = await read_db(); uid = str(interaction.user.id); tid = str(target.id)
        ensure_user(db, uid); ensure_user(db, tid)
        a = db['users'][uid]; b = db['users'][tid]
        if stawka <= 0:
            await interaction.response.send_message('Stawka musi być > 0', ephemeral=True); return
        if stawka > a.get('ka',0)*0.5 or stawka > b.get('ka',0)*0.5:
            await interaction.response.send_message('Stawka nie może przekraczać 50% salda któregokolwiek gracza.', ephemeral=True); return
        view = DuelView(interaction.user, target, stawka)
        await interaction.response.send_message(f'{target.mention}, {interaction.user.mention} wyzywa Cię na pojedynek o {stawka} KA. Akceptujesz?', view=view)

async def setup(bot):
    await bot.add_cog(Pojedynki(bot))
