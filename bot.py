import discord, os, asyncio, time, random
from discord.ext import commands
from dotenv import load_dotenv
import db_pg, items

load_dotenv()
TOKEN = os.getenv('TOKEN')
ATLANTYDA_CHANNEL = int(os.getenv('ATLANTYDA_CHANNEL_ID') or 0)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def in_game_channel(ctx):
    return ctx.channel and ctx.channel.id == ATLANTYDA_CHANNEL

# helper for pretty time remaining
def format_remaining(end_ts):
    left = max(0, end_ts - int(time.time()))
    days = left // 86400
    hours = (left % 86400) // 3600
    mins = (left % 3600) // 60
    return f"{days}d {hours}h {mins}m" if left>0 else "0m"

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
    await db_pg.init_db()
    bot.loop.create_task(hourly_event_loop())
    bot.loop.create_task(war_monitor_loop())
    try:
        await bot.load_extension('guide')
    except Exception as e:
        print('Guide extension not loaded:', e)

# START flow
@bot.command(name='start')
async def start(ctx):
    if not in_game_channel(ctx):
        await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    existing = await db_pg.get_player(ctx.author.id)
    if existing:
        await ctx.send('Masz już postać. Użyj !panel'); return
    await ctx.send(f'{ctx.author.mention} Wybierz klasę: 1) Wojownik 2) Zabójca 3) Mag 4) Kapłan (napisz numer)')
    def check(m): return m.author==ctx.author and m.channel==ctx.channel
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        classes = {'1':'Wojownik','2':'Zabójca','3':'Mag','4':'Kapłan'}
        if msg.content.strip() not in classes:
            await ctx.send('Niepoprawny wybór.'); return
        klass = classes[msg.content.strip()]
        await ctx.send('Rozdaj 20 punktów: wpisz 4 liczby: Siła Zręczność Mądrość Charyzma (sum=20)')
        msg2 = await bot.wait_for('message', timeout=120.0, check=check)
        parts = msg2.content.split()
        if len(parts)!=4:
            await ctx.send('Niepoprawny format.'); return
        s,d,w,c = map(int, parts)
        if s+d+w+c != 20:
            await ctx.send('Suma musi wynosić 20.'); return
        bonuses = {'Wojownik':{'hp_bonus':5,'str':2}, 'Zabójca':{'dex':3,'str':1}, 'Mag':{'wis':3,'dex':1}, 'Kapłan':{'wis':2,'cha':2}}
        base = {'str': s + bonuses.get(klass,{}).get('str',0),
                'dex': d + bonuses.get(klass,{}).get('dex',0),
                'wis': w + bonuses.get(klass,{}).get('wis',0),
                'cha': c + bonuses.get(klass,{}).get('cha',0),
                'hp_bonus': bonuses.get(klass,{}).get('hp_bonus',0)}
        await db_pg.create_player(ctx.author.id, ctx.author.name, klass, base, gold=200)
        await ctx.send(f'Stworzono postać **{ctx.author.name}** jako **{klass}** — powodzenia!')
    except asyncio.TimeoutError:
        await ctx.send('Czas na tworzenie postaci minął.')

# PANEL command
@bot.command(name='panel')
async def panel(ctx):
    if not in_game_channel(ctx):
        await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    p = await db_pg.get_player(ctx.author.id)
    if not p:
        await ctx.send('Nie masz postaci. Użyj !start'); return
    inv = await db_pg.get_inventory(ctx.author.id)
    inv_text = ', '.join([f"{i['item_id']} x{i['qty']}" for i in inv]) or 'Brak'
    embed = discord.Embed(title=f"🌊 Panel — {p['name']}", color=discord.Color.blue())
    embed.add_field(name='Klasa', value=p['class'], inline=True)
    embed.add_field(name='Poziom', value=str(p['level']), inline=True)
    embed.add_field(name='HP', value=f"{p['hp']}/{p['max_hp']}", inline=True)
    embed.add_field(name='Złoto', value=str(p['gold']), inline=True)
    embed.add_field(name='Siła', value=str(p['str']), inline=True)
    embed.add_field(name='Zręczność', value=str(p['dex']), inline=True)
    embed.add_field(name='Mądrość', value=str(p['wis']), inline=True)
    embed.add_field(name='Charyzma', value=str(p['cha']), inline=True)
    embed.add_field(name='Ekwipunek', value=inv_text, inline=False)
    await ctx.send(embed=embed)

# PVE command
@bot.command(name='pve')
async def pve(ctx):
    if not in_game_channel(ctx):
        await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    p = await db_pg.get_player(ctx.author.id)
    if not p: await ctx.send('Nie masz postaci.'); return
    lvl = p['level']
    enemy_hp = 20 + lvl*6 + random.randint(0,8)
    enemy_atk = 2 + lvl + random.randint(0,3)
    p_hp = p['hp']; e_hp = enemy_hp; log=[]
    while p_hp>0 and e_hp>0:
        dmg = max(1, p['str'] + random.randint(1,6))
        e_hp -= dmg; log.append(f'Zadajesz {dmg}. Enemy HP {max(0,e_hp)}')
        if e_hp<=0: break
        ed = max(1, enemy_atk + random.randint(0,4))
        p_hp -= ed; log.append(f'Wróg zadaje {ed}. Twoje HP {max(0,p_hp)}')
    if p_hp>0:
        gold = 25 + lvl*7; xp = 15 + lvl*3
        await db_pg.update_player(ctx.author.id, gold=p['gold']+gold, xp=p['xp']+xp, hp=p_hp)
        loot_msg = ''
        if random.random() < 0.25:
            it = random.choice(items.ITEMS)
            await db_pg.add_item(ctx.author.id, it['id'])
            loot_msg = f'Zdobyłeś: **{it["name"]}**'
        embed = discord.Embed(title='⚔️ PvE — Zwycięstwo!', color=discord.Color.green())
        embed.add_field(name='Nagroda', value=f'+{gold}💧, +{xp} XP', inline=False)
        if loot_msg: embed.add_field(name='Loot', value=loot_msg, inline=False)
        embed.add_field(name='Log (ostatnie)', value='\n'.join(log[-6:]), inline=False)
        await ctx.send(embed=embed)
    else:
        await db_pg.update_player(ctx.author.id, hp=1)
        embed = discord.Embed(title='💀 PvE — Porażka', description='Zostałeś pokonany. Odrodzisz się z 1 HP.', color=discord.Color.dark_gray())
        embed.add_field(name='Log', value='\n'.join(log[-6:]), inline=False)
        await ctx.send(embed=embed)

# PVP command
@bot.command(name='pvp')
async def pvp(ctx, target: discord.Member=None, stake: int=0):
    if not in_game_channel(ctx): await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    if target is None: await ctx.send('Podaj przeciwnika!'); return
    if target.id == ctx.author.id: await ctx.send('Nie możesz wyzwać siebie.'); return
    p1 = await db_pg.get_player(ctx.author.id); p2 = await db_pg.get_player(target.id)
    if not p1 or not p2: await ctx.send('Obie strony muszą mieć postacie.'); return
    if stake>0 and p1['gold']<stake: await ctx.send('Nie masz złota.'); return
    if stake>0 and p2['gold']<stake: await ctx.send('Przeciwnik nie ma złota.'); return
    await ctx.send(f'{target.mention}, {ctx.author.mention} wyzwał Cię na PvP (stawka {stake}💧). Napisz "akceptuj" aby przyjąć (60s).')
    def check(m): return m.author==target and m.channel==ctx.channel and m.content.lower() in ('akceptuj','tak','accept')
    try:
        await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('Wyzwanie wygasło.'); return
    rounds=3; s1=0; s2=0; logs=[]
    for r in range(rounds):
        r1 = random.randint(1,20) + p1['str'] + p1['dex']
        r2 = random.randint(1,20) + p2['str'] + p2['dex']
        if r1>=r2: s1+=1; logs.append(f'R{r+1}: {ctx.author.name} wygrywa ({r1} vs {r2})')
        else: s2+=1; logs.append(f'R{r+1}: {target.name} wygrywa ({r2} vs {r1})')
    if s1>s2:
        await db_pg.update_player(ctx.author.id, gold=p1['gold']+stake if stake>0 else p1['gold'])
        await db_pg.update_player(target.id, gold=p2['gold']-stake if stake>0 else p2['gold'])
        await ctx.send(f'🏆 {ctx.author.mention} wygrał PvP!\n' + '\n'.join(logs))
        # increment war wins if in war
        g1 = await db_pg.get_player_guild(ctx.author.id); g2 = await db_pg.get_player_guild(target.id)
        if g1 and g2 and g1['guild_id']!=g2['guild_id']:
            now=int(time.time()); wars = await db_pg.get_active_wars(now)
            for w in wars:
                if (w['guild_a']==g1['guild_id'] and w['guild_b']==g2['guild_id']) or (w['guild_a']==g2['guild_id'] and w['guild_b']==g1['guild_id']):
                    if w['guild_a']==g1['guild_id']: await db_pg.increment_war_win(w['id'],'a')
                    else: await db_pg.increment_war_win(w['id'],'b')
    else:
        await db_pg.update_player(target.id, gold=p2['gold']+stake if stake>0 else p2['gold'])
        await db_pg.update_player(ctx.author.id, gold=p1['gold']-stake if stake>0 else p1['gold'])
        await ctx.send(f'🏆 {target.mention} wygrał PvP!\n' + '\n'.join(logs))
        g1 = await db_pg.get_player_guild(ctx.author.id); g2 = await db_pg.get_player_guild(target.id)
        if g1 and g2 and g1['guild_id']!=g2['guild_id']:
            now=int(time.time()); wars = await db_pg.get_active_wars(now)
            for w in wars:
                if (w['guild_a']==g1['guild_id'] and w['guild_b']==g2['guild_id']) or (w['guild_a']==g2['guild_id'] and w['guild_b']==g1['guild_id']):
                    if w['guild_a']==g2['guild_id']: await db_pg.increment_war_win(w['id'],'a')
                    else: await db_pg.increment_war_win(w['id'],'b')

# SHOP commands
@bot.command(name='shop')
async def shop(ctx):
    if not in_game_channel(ctx): await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    text = '\n'.join([f"{it['id']}: {it['name']} — {it.get('price','?')}💧 (lvl {it['level']})" for it in items.ITEMS])
    embed = discord.Embed(title='🏪 Sklep Atlantyda', description=text, color=discord.Color.gold())
    embed.set_footer(text='Aby kupić: !buy <item_id>')
    await ctx.send(embed=embed)

@bot.command(name='buy')
async def buy(ctx, item_id:str):
    if not in_game_channel(ctx): await ctx.send('Gra działa tylko na kanale #atlantyda'); return
    p = await db_pg.get_player(ctx.author.id)
    if not p: await ctx.send('Nie masz postaci.'); return
    it = next((i for i in items.ITEMS if i['id']==item_id), None)
    if not it: await ctx.send('Nie znaleziono przedmiotu.'); return
    if p['level'] < it.get('level',1): await ctx.send(f'Potrzebujesz poziomu {it['level']}'); return
    if p['gold'] < it.get('price',999999): await ctx.send('Nie masz złota.'); return
    await db_pg.update_player(ctx.author.id, gold=p['gold']-it['price'])
    await db_pg.add_item(ctx.author.id, it['id'])
    await ctx.send(f'Kupiono **{it['name']}** za {it['price']}💧')

# GUILD commands (create/join/war initiate)
@bot.group(name='guild', invoke_without_command=True)
async def guild(ctx): await ctx.send('Use: !guild create <name> | !guild join <name> | !guild war <name>')

@guild.command(name='create')
async def guild_create(ctx, *, name:str):
    if not in_game_channel(ctx): await ctx.send('Gra tylko na kanale #atlantyda'); return
    existing = await db_pg.get_guild_by_name(name)
    if existing: await ctx.send('Gildia istnieje.'); return
    gid = await db_pg.create_guild(name, ctx.author.id)
    await ctx.send(f'Stworzono gildię **{name}** (ID {gid}).')

@guild.command(name='join')
async def guild_join(ctx, *, name:str):
    if not in_game_channel(ctx): await ctx.send('Gra tylko na kanale #atlantyda'); return
    g = await db_pg.get_guild_by_name(name)
    if not g: await ctx.send('Nie znaleziono gildii.'); return
    await db_pg.join_guild(g['id'], ctx.author.id)
    await ctx.send(f'Dołączyłeś do **{name}**')

@guild.command(name='war')
async def guild_war(ctx, *, target_name:str):
    if not in_game_channel(ctx): await ctx.send('Gra tylko na kanale #atlantyda'); return
    pg = await db_pg.get_player_guild(ctx.author.id); 
    if not pg: await ctx.send('Musisz być w gildii.'); return
    if pg['role']!='Mistrz': await ctx.send('Tylko Mistrz może wywołać wojnę.'); return
    target = await db_pg.get_guild_by_name(target_name)
    if not target: await ctx.send('Nie znaleziono gildii.'); return
    leader = target['leader']
    leader_user = await bot.fetch_user(leader)
    # send accept view
    view = discord.ui.View(timeout=60*60*24)
    async def accept_cb(interaction):
        start_ts = int(time.time()); end_ts = start_ts + 3*24*3600
        war_id = await db_pg.create_war(pg['guild_id'], target['id'], start_ts, end_ts)
        # send nice embed to channel announcing war
        g1 = await db_pg.get_guild_by_id(pg['guild_id']); g2 = await db_pg.get_guild_by_id(target['id'])
        em = discord.Embed(title='🏰 Wojna Gildii Rozpoczęta!', color=discord.Color.red())
        em.add_field(name='Gildia A', value=g1['name'], inline=True)
        em.add_field(name='Gildia B', value=g2['name'], inline=True)
        em.add_field(name='Czas trwania', value='3 dni', inline=False)
        ch = bot.get_channel(ATLANTYDA_CHANNEL)
        if ch: await ch.send(embed=em)
        await interaction.response.send_message('Wojna rozpoczęta!', ephemeral=True)
    async def decline_cb(interaction):
        await interaction.response.send_message('Wyzwanie odrzucone.', ephemeral=True)
    btn_accept = discord.ui.Button(label='Akceptuj', style=discord.ButtonStyle.success); btn_decline = discord.ui.Button(label='Odrzuc', style=discord.ButtonStyle.danger)
    btn_accept.callback = accept_cb; btn_decline.callback = decline_cb
    view.add_item(btn_accept); view.add_item(btn_decline)
    await leader_user.send(f'Gildia **{(await db_pg.get_guild_by_id(pg["guild_id"]))["name"]}** wyzwała Twoją gildię do wojny. Akceptujesz?', view=view)
    await ctx.send('Wyzwanie wysłane do lidera docelowej gildii.')

# war monitor loop with nicer end embed
async def war_monitor_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(ATLANTYDA_CHANNEL)
    while not bot.is_closed():
        now = int(time.time())
        wars = await db_pg.get_active_wars(now)
        for w in wars:
            if w['end_ts'] <= now:
                res = await db_pg.end_war(w['id'])
                if channel:
                    if res and res.get('winner'):
                        gw = await db_pg.get_guild_by_id(res['winner'])
                        embed = discord.Embed(title='🏁 Wojna zakończona', description=f'Zwycięzca: **{gw["name"]}**', color=discord.Color.gold())
                        embed.add_field(name='Wynik', value=f"{res['wins'][0]} - {res['wins'][1]}")
                        await channel.send(embed=embed)
                    else:
                        await channel.send('🏁 Wojna zakończona remisem.')
        await asyncio.sleep(60)

# hourly events with embed and small effect tracking
async def hourly_event_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(ATLANTYDA_CHANNEL)
    events = [
        ('🌑 Atak Cieni','PvE +20% trudności'),
        ('🌊 Błogosławieństwo Posejdona','Gildie w wojnie +1 pkt za PvP'),
        ('🔥 Magma','Ataki magiczne +5 dmg')
    ]
    while not bot.is_closed():
        ev = random.choice(events)
        if channel:
            embed = discord.Embed(title='⏳ Event godzinowy', description=f'{ev[0]} — {ev[1]}', color=discord.Color.blue())
            await channel.send(embed=embed)
        await asyncio.sleep(3600)

# ranking command
@bot.command(name='ranking')
async def ranking(ctx):
    if not in_game_channel(ctx): await ctx.send('Gra tylko na kanale #atlantyda'); return
    pool = await db_pg.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT name, level, gold FROM players ORDER BY level DESC, gold DESC LIMIT 10')
    txt = '\n'.join([f"{r['name']} — lvl {r['level']} ({r['gold']}💧)" for r in rows]) or 'Brak graczy'
    embed = discord.Embed(title='🏆 Ranking TOP10', description=txt, color=discord.Color.purple())
    await ctx.send(embed=embed)

if __name__=='__main__':
    bot.run(TOKEN)
