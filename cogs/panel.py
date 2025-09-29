import discord, time, random
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check

def get_cog(bot, *names):
    names = [n.lower() for n in names]
    for k, cog in bot.cogs.items():
        if k.lower() in names:
            return cog
    return None

class PanelView(ui.View):
    def __init__(self, bot, owner):
        super().__init__(timeout=180)
        self.bot = bot
        self.owner = owner

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.owner.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('⛔ To nie Twój panel!', ephemeral=True)
            return False
        return True

    @ui.button(label='💼 Praca', style=discord.ButtonStyle.green)
    async def work(self, interaction: Interaction, button: ui.Button):
        praca = get_cog(self.bot, 'Praca', 'praca')
        if praca and hasattr(praca, 'do_work'):
            res = await praca.do_work(interaction.user.id)
            if res is None:
                db = await read_db(); left = 10*60 - (int(time.time()) - db['users'][str(interaction.user.id)].get('last_work',0))
                await interaction.response.send_message(f'⏳ Możesz pracować za {left//60}m {left%60}s.', ephemeral=True); return
            await interaction.response.send_message(f'🛠️ Pracowałeś i zarobiłeś **{res} KA**!', ephemeral=False); return
        await interaction.response.send_message('🛠️ Praca chwilowo niedostępna.', ephemeral=True)

    @ui.button(label='💰 Saldo', style=discord.ButtonStyle.primary)
    async def saldo(self, interaction: Interaction, button: ui.Button):
        econ = get_cog(self.bot, 'Ekonomia', 'ekonomia')
        if econ and hasattr(econ, 'saldo'):
            await econ.saldo(interaction); return
        db = await read_db(); uid = str(interaction.user.id); ensure_user(db, uid); u = db['users'][uid]
        await interaction.response.send_message(f"💰 Saldo: {u.get('ka',0)} KA\nPoziom: {u.get('level',0)}\nRep: {u.get('reputation',0)}", ephemeral=True)

    @ui.button(label='🎰 Kasyno', style=discord.ButtonStyle.danger)
    async def kasyno(self, interaction: Interaction, button: ui.Button):
        kas = get_cog(self.bot, 'Kasyno', 'kasyno')
        if kas and hasattr(kas, 'kasyno'):
            try:
                await kas.kasyno(interaction, 100); return
            except Exception:
                pass
        db = await read_db(); uid = str(interaction.user.id); ensure_user(db, uid); u = db['users'][uid]
        bet = 100
        if u.get('ka',0) < bet:
            await interaction.response.send_message(f'Nie masz {bet} KA!', ephemeral=True); return
        win = random.choice([True, False])
        if win:
            u['ka'] += bet; u['earned_total'] += bet; await write_db(db); await interaction.response.send_message(f'🎉 Wygrałeś {bet} KA!', ephemeral=False)
        else:
            u['ka'] = max(0, u.get('ka',0)-bet); u['spent_total'] += bet; u['reputation'] = max(0,u.get('reputation',0)-1); await write_db(db); await interaction.response.send_message(f'💀 Przegrałeś {bet} KA i -1 reputacji.', ephemeral=False)

    @ui.button(label='⚔️ Pojedynek', style=discord.ButtonStyle.blurple)
    async def duel(self, interaction: Interaction, button: ui.Button):
        modal = DuelModal(self.bot); await interaction.response.send_modal(modal)

    @ui.button(label='🎒 Ekwipunek', style=discord.ButtonStyle.secondary)
    async def inv(self, interaction: Interaction, button: ui.Button):
        db = await read_db(); uid = str(interaction.user.id); ensure_user(db, uid); u = db['users'][uid]
        items = u.get('items',{})
        if not items:
            await interaction.response.send_message('🎒 Ekwipunek pusty.', ephemeral=True); return
        await interaction.response.send_message(embed=discord.Embed(title='🎒 Ekwipunek', description='\n'.join([f"{k}: {v}" for k,v in items.items()])), ephemeral=True)

    @ui.button(label='🔧 Panel Admina', style=discord.ButtonStyle.blurple)
    async def admin(self, interaction: Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('Tylko admin.', ephemeral=True); return
        modal = AdminModal(self.bot); await interaction.response.send_modal(modal)

class DuelModal(ui.Modal, title='Wyzwanie - target i stawka'):
    target = ui.TextInput(label='Target (ID lub @mention)', placeholder='@User lub ID', required=True)
    stawka = ui.TextInput(label='Stawka (liczba KA)', placeholder='50', required=True, max_length=10)
    def __init__(self, bot):
        super().__init__(); self.bot = bot
    async def on_submit(self, interaction: Interaction):
        raw_t = self.target.value.strip(); raw_s = self.stawka.value.strip()
        try:
            stake = int(raw_s)
        except:
            await interaction.response.send_message('Niepoprawna stawka.', ephemeral=True); return
        if raw_t.startswith('<@') and raw_t.endswith('>'):
            raw_t = raw_t.replace('<@','').replace('>','').replace('!','')
        try:
            tid = int(raw_t)
        except:
            await interaction.response.send_message('Niepoprawny target.', ephemeral=True); return
        duel_cog = get_cog(self.bot, 'Pojedynki', 'pojedynki')
        if duel_cog and hasattr(duel_cog, 'pojedynek'):
            member = interaction.guild.get_member(tid) if interaction.guild else None
            await duel_cog.pojedynek(interaction, member, stake); return
        db = await read_db(); uid = str(interaction.user.id); tid_s = str(tid); ensure_user(db, uid); ensure_user(db, tid_s)
        a = db['users'][uid]; b = db['users'][tid_s]
        if stake <=0 or stake > a.get('ka',0)*0.5 or stake > b.get('ka',0)*0.5:
            await interaction.response.send_message('Niepoprawna stawka lub zbyt wysoka.', ephemeral=True); return
        import random
        chance = 50 + (a.get('level',0)-b.get('level',0))*5
        roll = random.randint(1,100)
        if roll <= chance:
            a['ka'] += stake; b['ka'] = max(0,b.get('ka',0)-stake); a['earned_total'] += stake; b['spent_total'] += stake; a['xp'] = a.get('xp',0)+20; a['level'] = a.get('xp',0)//100
            await write_db(db); await interaction.response.send_message(f'🏆 <@{interaction.user.id}> wygrał {stake} KA!')
        else:
            b['ka'] += stake; a['ka'] = max(0,a.get('ka',0)-stake); b['earned_total'] += stake; a['spent_total'] += stake; b['xp'] = b.get('xp',0)+20; b['level'] = b.get('xp',0)//100
            await write_db(db); await interaction.response.send_message(f'🏆 <@{tid}> wygrał {stake} KA!')

class AdminModal(ui.Modal, title='Panel Admina - akcja'):
    action = ui.TextInput(label='Akcja (dodajka/banuj/ostrzez/gildia_zmien)', required=True)
    target = ui.TextInput(label='Target (ID lub @mention)', required=False)
    amount = ui.TextInput(label='Kwota / nazwa', required=False)
    reason = ui.TextInput(label='Powód (opcjonalnie)', required=False)
    def __init__(self, bot):
        super().__init__(); self.bot = bot
    async def on_submit(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('Brak uprawnień.', ephemeral=True); return
        act = self.action.value.strip().lower(); tgt = self.target.value.strip(); amt = self.amount.value.strip(); reason = self.reason.value.strip() or 'Brak powodu'
        if tgt.startswith('<@') and tgt.endswith('>'):
            tgt = tgt.replace('<@','').replace('>','').replace('!','')
        target_id = None
        try:
            target_id = int(tgt) if tgt else None
        except:
            target_id = None
        admin = get_cog(self.bot, 'AdminPanel', 'admin_panel')
        if admin:
            try:
                if act.startswith('dodaj'):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await admin.dodajka(interaction, member, int(amt)); return
                if act in ('banuj','ban'):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await admin.banuj(interaction, member, reason); return
                if act in ('ostrzez','ukarz','warn'):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await admin.ostrzez(interaction, member, reason); return
            except Exception:
                pass
        db = await read_db()
        if act.startswith('dodaj'):
            if not target_id or not amt:
                await interaction.response.send_message('Podaj target i kwotę.', ephemeral=True); return
            uid = str(target_id); ensure_user(db, uid); db['users'][uid]['ka'] += int(amt); db['users'][uid]['earned_total'] += int(amt); await write_db(db); await interaction.response.send_message('OK', ephemeral=True); return
        await interaction.response.send_message('Nieznana akcja.', ephemeral=True)

class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='panel', description='Otwiera Twój panel (gracz/admin).')
    async def panel(self, interaction: Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db(); uid = str(interaction.user.id); ensure_user(db, uid); u = db['users'][uid]
        embed = discord.Embed(title=f'🎮 Panel — {interaction.user.display_name}', description='Wybierz akcję.', color=discord.Color.blurple())
        embed.add_field(name='💰 KA', value=str(u.get('ka',0)), inline=True); embed.add_field(name='📈 Poziom', value=str(u.get('level',0)), inline=True); embed.add_field(name='⭐ Reputacja', value=str(u.get('reputation',0)), inline=True)
        view = PanelView(self.bot, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Panel(bot))
