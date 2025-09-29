import discord, random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_ka
from discord import ui

class Ekonomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # RP-rewards: tylko na kanale Atlantyda, tylko użytkownicy, >=120 znaków, raz na 24h
        if message.author.bot: return
        if not channel_check(message.channel): return
        content = message.content.strip()
        if len(content) >= 120:
            db = await read_db()
            uid = str(message.author.id)
            ensure_user(db, uid)
            user = db['users'][uid]
            now = int(time.time())
            if now - user.get('last_rp_reward',0) >= 24*3600:
                user['ka'] += 50
                user['reputation'] += 1
                user['last_rp_reward'] = now
                user['earned_total'] += 50
                user['rp_xp'] = user.get('rp_xp',0) + 10
                # small chance of RP artefact
                if random.randint(1,100) <= 8:
                    user['items']['perla_madrosci'] = user['items'].get('perla_madrosci',0) + 1
                user['level'] = level_from_ka(user['earned_total'] + user['spent_total'])
                await write_db(db)
                try:
                    await message.channel.send(f'{message.author.mention} otrzymuje +50 KA i +1 reputacji za wkład RP!')
                except Exception:
                    pass

    @app_commands.command(name='saldo', description='Pokaż swoje saldo, poziom i reputację.')
    async def saldo(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        badges = ', '.join(user.get('badges',[])[:5]) or 'Brak'
        await interaction.response.send_message(
            f"Saldo: {user['ka']} KA\nPoziom: {user['level']}\nReputacja: {user['reputation']}\nOdznaki: {badges}")

    @app_commands.command(name='ranking', description='Pokaż ranking top 10 (KA/reputacja/poziom).')
    async def ranking(self, interaction: discord.Interaction, typ: str = 'ka'):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        typ = typ.lower()
        db = await read_db()
        users = db.get('users',{})
        if typ == 'reputacja' or typ=='rep':
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('reputation',0), reverse=True)
        elif typ == 'level' or typ=='poziom':
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('level',0), reverse=True)
        else:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)
        text = []
        for i,(uid,data) in enumerate(sorted_u[:10]):
            text.append(f"{i+1}. <@{uid}> - {data.get('ka',0)} KA / Lvl {data.get('level',0)} / Rep {data.get('reputation',0)}")
        await interaction.response.send_message('\n'.join(text) or 'Brak danych.')

async def setup(bot):
    await bot.add_cog(Ekonomia(bot))
