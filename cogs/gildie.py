import discord, random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Kradzieze(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='kradnij', description='Spróbuj ukraść KA od użytkownika.')
    async def kradnij(self, interaction: discord.Interaction, target: discord.Member, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True)
            return
        if target.bot:
            await interaction.response.send_message('Nie można kraść od bota.', ephemeral=True); return
        if kwota <=0:
            await interaction.response.send_message('Kwota musi być >0', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id); tid = str(target.id)
        ensure_user(db, uid); ensure_user(db, tid)
        thief = db['users'][uid]; victim = db['users'][tid]
        now = int(time.time())
        # daily limit 3 attempts (resets daily)
        if thief.get('steal_count',0) >= 3 and now - thief.get('last_steal_time',0) < 24*3600:
            await interaction.response.send_message('Osiągnięto limit 3 prób kradzieży na dobę.', ephemeral=True); return
        if now - thief.get('steal_ts',0) < 3600:
            await interaction.response.send_message('Cooldown kradzieży: 1 godzina.', ephemeral=True); return
        max_amount = int(victim['ka']*0.2)
        if max_amount <=0:
            await interaction.response.send_message('Cel nie ma nic do ukradzenia.', ephemeral=True); return
        if kwota > max_amount:
            await interaction.response.send_message(f'Maksymalnie możesz próbować ukraść {max_amount} KA (20% salda celu).', ephemeral=True); return
        # compute success chance
        base = 40
        if 'amulet' in victim.get('items',{}):
            base -= 20
        # thief items
        if 'eliksir' in thief.get('items',{}):
            base += 20
            # consume one elixir
            thief['items']['eliksir'] -= 1
            if thief['items']['eliksir'] <=0:
                del thief['items']['eliksir']
        base += (thief.get('level',0)-victim.get('level',0))*3
        success = random.randint(1,100) <= base
        thief['steal_ts'] = now
        thief['steal_count'] = thief.get('steal_count',0)+1
        thief['last_steal_time'] = thief.get('last_steal_time', now)
        if success:
            stolen = min(kwota, victim['ka'])
            victim['ka'] -= stolen
            thief['ka'] += stolen
            thief['earned_total'] += stolen
            victim['spent_total'] += stolen
            thief['reputation'] += 2
            thief['badges'] = list(set(thief.get('badges',[])+['Cichy Złodziej']))
            await write_db(db)
            await interaction.response.send_message(f'Udana kradzież! Zyskałeś {stolen} KA.')
        else:
            penalty = min(thief['ka'], int(kwota*0.5)+50)
            thief['ka'] -= penalty
            thief['reputation'] -= 3
            thief['spent_total'] += penalty
            thief['badges'] = list(set(thief.get('badges',[])+['Przechwycony']))
            await write_db(db)
            await interaction.response.send_message(f'Nieudana kradzież. Tracisz {penalty} KA i reputację.')

async def setup(bot):
    await bot.add_cog(Kradzieze(bot))
