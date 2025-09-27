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
                # szansa na artefakt RP
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
        if typ in ['reputacja','rep']:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('reputation',0), reverse=True)
        elif typ in ['level','poziom']:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('level',0), reverse=True)
        else:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)
        text = []
        for i,(uid,data) in enumerate(sorted_u[:10]):
            text.append(f"{i+1}. <@{uid}> - {data.get('ka',0)} KA / Lvl {data.get('level',0)} / Rep {data.get('reputation',0)}")
        await interaction.response.send_message('\n'.join(text) or 'Brak danych.')

    # 🔹 Daily nagroda
    @app_commands.command(name='daily', description='Odbierz swoją dzienną nagrodę.')
    async def daily(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        teraz = int(time.time())
        if teraz - user.get('daily',0) < 24*3600:
            pozostalo = int((24*3600 - (teraz - user['daily'])) // 3600)
            await interaction.response.send_message(f"❌ Już odebrałeś nagrodę dnia. Spróbuj ponownie za {pozostalo} godzin.")
            return
        nagroda = random.randint(100,300)
        user['ka'] += nagroda
        user['earned_total'] += nagroda
        user['daily'] = teraz
        user['level'] = level_from_ka(user['earned_total'] + user['spent_total'])
        await write_db(db)
        await interaction.response.send_message(f"✅ Odebrałeś nagrodę dnia: **{nagroda} KA**")

    # 🔹 Praca
    @app_commands.command(name='work', description='Idź do pracy i zarób monety.')
    async def work(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        teraz = int(time.time())
        if teraz - user.get('work',0) < 3600:
            pozostalo = int((3600 - (teraz - user['work'])) // 60)
            await interaction.response.send_message(f"❌ Już pracowałeś! Spróbuj ponownie za {pozostalo} minut.")
            return
        zarobek = random.randint(50,150)
        prace = ["programistą", "kelnerem", "rolnikiem", "górnikiem", "budowlańcem"]
        praca = random.choice(prace)
        user['ka'] += zarobek
        user['earned_total'] += zarobek
        user['work'] = teraz
        user['level'] = level_from_ka(user['earned_total'] + user['spent_total'])
        await write_db(db)
        await interaction.response.send_message(f"💼 Pracowałeś jako **{praca}** i zarobiłeś **{zarobek} KA**!")

    # 🔹 Daj monety
    @app_commands.command(name='daj', description='Przekaż KA innemu użytkownikowi.')
    async def daj(self, interaction: discord.Interaction, osoba: discord.Member, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        if kwota <= 0:
            await interaction.response.send_message("❌ Kwota musi być większa od zera.")
            return
        db = await read_db()
        nadawca_id = str(interaction.user.id)
        odbiorca_id = str(osoba.id)
        ensure_user(db, nadawca_id)
        ensure_user(db, odbiorca_id)
        if db['users'][nadawca_id]['ka'] < kwota:
            await interaction.response.send_message("❌ Nie masz wystarczająco KA.")
            return
        db['users'][nadawca_id]['ka'] -= kwota
        db['users'][nadawca_id]['spent_total'] += kwota
        db['users'][odbiorca_id]['ka'] += kwota
        db['users'][odbiorca_id]['earned_total'] += kwota
        await write_db(db)
        await interaction.response.send_message(f"✅ Przekazałeś **{kwota} KA** użytkownikowi {osoba.mention}")

async def setup(bot):
    await bot.add_cog(Ekonomia(bot))
