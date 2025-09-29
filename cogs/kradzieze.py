import random
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Kradzieze(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='kradziez', description='Spróbuj ukraść KA od innego gracza (ryzyko).')
    async def kradziez(self, interaction: app_commands.Context, target: discord.Member):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        if target.bot:
            await interaction.response.send_message('Nie możesz kraść od bota.', ephemeral=True); return
        db = await read_db(); uid = str(interaction.user.id); tid = str(target.id)
        ensure_user(db, uid); ensure_user(db, tid)
        a = db['users'][uid]; b = db['users'][tid]
        amount = min( int(b.get('ka',0)*0.2), 100 )
        if amount <= 0:
            await interaction.response.send_message('Cel nie ma nic do kradzieży.', ephemeral=True); return
        success = random.randint(1,100) <= 40
        if success:
            a['ka'] += amount; b['ka'] = max(0, b['ka'] - amount)
            await write_db(db)
            await interaction.response.send_message(f'✅ Udało się ukraść {amount} KA od {target.mention}!')
        else:
            a['reputation'] = max(0, a.get('reputation',0)-1)
            await write_db(db)
            await interaction.response.send_message(f'❌ Nieudana kradzież. Tracisz 1 reputacji.', ephemeral=True)

async def setup(bot):
    await bot.add_cog(Kradzieze(bot))
