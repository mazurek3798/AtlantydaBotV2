import discord
from discord.ext import commands, tasks
from discord import app_commands
from pathlib import Path
import sqlite3, time, random, json

DB = Path(__file__).parent.parent / "atlantyda.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Ensure tables (idempotent)
c.execute("""CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    lvl INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 100,
    strength INTEGER DEFAULT 5,
    dexterity INTEGER DEFAULT 5,
    wisdom INTEGER DEFAULT 5,
    charisma INTEGER DEFAULT 5,
    hp INTEGER DEFAULT 100,
    klass TEXT DEFAULT ''
)""")
c.execute("""CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_id TEXT,
    qty INTEGER DEFAULT 1
)""")
c.execute("""CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    rarity TEXT,
    stats TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS guilds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    owner_id INTEGER,
    members TEXT,
    gold INTEGER DEFAULT 0,
    prestige INTEGER DEFAULT 0
)""")
c.execute("""CREATE TABLE IF NOT EXISTS wars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_a TEXT,
    guild_b TEXT,
    start_ts INTEGER,
    end_ts INTEGER,
    active INTEGER DEFAULT 1,
    score_a INTEGER DEFAULT 0,
    score_b INTEGER DEFAULT 0
)""")
conn.commit()

# seed items
def seed_items():
    examples = [
        ("potion_small","Mikstura zdrowia","consumable","common",'{"heal":50}'),
        ("sword_wood","Miecz drewniany","weapon","common",'{"attack":2}'),
        ("armor_leather","Zbroja skórzana","armor","common",'{"defense":2}'),
        ("trophy_pvp","Trofeum","pvp","rare",'{"all":2}'),
        ("blade_victory","Ostrze zwycięzcy","pvp","epic",'{"strength":10}'),
        ("crown_atlantyda","Korona Atlantydy","unique","unique",'{"strength":20,"dexterity":20,"wisdom":20,"charisma":20}')
    ]
    for it in examples:
        c.execute("INSERT OR IGNORE INTO items (item_id, name, type, rarity, stats) VALUES (?,?,?,?,?)", it)
    conn.commit()

seed_items()

def make_embed(title, desc, color=discord.Color.blue()):
    return discord.Embed(title=title, description=desc, color=color)

def get_player(uid):
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id=?", (uid,))
    return cur.fetchone()

def create_player(user, klass=""):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO players (user_id, name, klass) VALUES (?,?,?)", (user.id, user.display_name, klass))
    conn.commit()

def add_item(uid, item_id, qty=1):
    cur = conn.cursor()
    cur.execute("SELECT qty FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id))
    r = cur.fetchone()
    if r:
        cur.execute("UPDATE inventory SET qty=qty+? WHERE user_id=? AND item_id=?", (qty, uid, item_id))
    else:
        cur.execute("INSERT INTO inventory (user_id, item_id, qty) VALUES (?,?,?)", (uid, item_id, qty))
    conn.commit()

def remove_item(uid, item_id, qty=1):
    cur = conn.cursor()
    cur.execute("SELECT qty FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id))
    r = cur.fetchone()
    if not r:
        return False
    if r["qty"] <= qty:
        cur.execute("DELETE FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id))
    else:
        cur.execute("UPDATE inventory SET qty=qty-? WHERE user_id=? AND item_id=?", (qty, uid, item_id))
    conn.commit()
    return True

def get_inventory(uid):
    cur = conn.cursor()
    cur.execute("SELECT i.item_id, it.name, i.qty, it.rarity FROM inventory i JOIN items it ON i.item_id=it.item_id WHERE i.user_id=?", (uid,))
    return cur.fetchall()

def give_xp(uid, amount):
    cur = conn.cursor()
    cur.execute("UPDATE players SET xp = xp + ? WHERE user_id=?", (amount, uid))
    cur.execute("SELECT xp, lvl FROM players WHERE user_id=?", (uid,))
    r = cur.fetchone()
    if r and r["xp"] >= r["lvl"]*100:
        newlvl = r["lvl"] + 1
        cur.execute("UPDATE players SET lvl=?, xp=0 WHERE user_id=?", (newlvl, uid))
    conn.commit()

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.war_task.start()

    def cog_unload(self):
        self.war_task.cancel()

    @app_commands.command(name="start", description="🌊 Stwórz postać w Atlantydzie")
    @app_commands.describe(klass="Wybierz klasę: wojownik/zabojca/mag/kaplan")
    async def start(self, interaction: discord.Interaction, klass: str = "wojownik"):
        create_player(interaction.user, klass)
        add_item(interaction.user.id, "potion_small", 2)
        e = make_embed("🌊 Witaj w Atlantydzie!", f"Twoja postać została stworzona jako **{klass}**. Użyj /profil.", discord.Color.blue())
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="profil", description="⚙️ Pokaż profil swojej postaci")
    async def profil(self, interaction: discord.Interaction):
        create_player(interaction.user)
        p = get_player(interaction.user.id)
        if not p:
            await interaction.response.send_message(embed=make_embed("❌ Brak postaci", "Użyj /start", discord.Color.blue()))
            return
        e = make_embed(f"⚙️ Profil — {p['name']}", f"Poziom: {p['lvl']} | XP: {p['xp']} | Złoto: {p['gold']}", discord.Color.blue())
        e.add_field(name="Statystyki", value=f"Siła 💪: {p['strength']}\nZręczność 🌀: {p['dexterity']}\nMądrość 📖: {p['wisdom']}\nCharyzma 👑: {p['charisma']}\nHP: {p['hp']}")
        e.add_field(name="Klasa", value=p['klass'] or "—")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="statystyki", description="Rozdziel punkty statystyk")
    @app_commands.describe(strengh="Ile punktów do Siły", dexterity="Ile do Zręczności", wisdom="Ile do Mądrości", charisma="Ile do Charyzmy")
    async def statystyki(self, interaction: discord.Interaction, strengh: int=0, dexterity: int=0, wisdom: int=0, charisma: int=0):
        create_player(interaction.user)
        uid = interaction.user.id
        cur = conn.cursor()
        cur.execute("UPDATE players SET strength=strength+?, dexterity=dexterity+?, wisdom=wisdom+?, charisma=charisma+? WHERE user_id=?",
                    (strengh, dexterity, wisdom, charisma, uid))
        conn.commit()
        await interaction.response.send_message(embed=make_embed("⚙️ Statystyki zaktualizowane", f"Dodano: Siła {strengh}, Zręczność {dexterity}, Mądrość {wisdom}, Charyzma {charisma}", discord.Color.blue()))

    @app_commands.command(name="ekwipunek", description="📦 Pokaż ekwipunek")
    async def ekwipunek(self, interaction: discord.Interaction):
        create_player(interaction.user)
        inv = get_inventory(interaction.user.id)
        if not inv:
            await interaction.response.send_message(embed=make_embed("📦 Ekwipunek", "Pusty", discord.Color.blue()))
            return
        desc = "\\n".join([f"{r['name']} x{r['qty']} ({r['rarity']})" for r in inv])
        await interaction.response.send_message(embed=make_embed("📦 Ekwipunek", desc, discord.Color.blue()))

    @app_commands.command(name="sklep", description="💰 Otwórz sklep")
    async def sklep(self, interaction: discord.Interaction):
        cur = conn.cursor()
        cur.execute("SELECT item_id, name, rarity FROM items")
        items = cur.fetchall()
        desc = "\\n".join([f"{r['name']} — id: `{r['item_id']}` ({r['rarity']})" for r in items])
        e = make_embed("💰 Sklep Atlantydy", desc, discord.Color.gold())
        e.add_field(name="Jak kupić", value="Użyj /kup [item_id] [qty]")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="kup", description="Kup przedmiot w sklepie")
    @app_commands.describe(item_id="ID przedmiotu", qty="Ilość")
    async def kup(self, interaction: discord.Interaction, item_id: str, qty: int = 1):
        create_player(interaction.user)
        cur = conn.cursor()
        cur.execute("SELECT * FROM items WHERE item_id=?", (item_id,))
        it = cur.fetchone()
        if not it:
            await interaction.response.send_message(embed=make_embed("❌ Nie znaleziono przedmiotu", "", discord.Color.gold()))
            return
        rarity = it["rarity"]
        price_map = {"common":50,"rare":200,"epic":800,"unique":5000}
        price = price_map.get(rarity, 100) * qty
        p = get_player(interaction.user.id)
        if p["gold"] < price:
            await interaction.response.send_message(embed=make_embed("❌ Za mało złota", f"Potrzebujesz {price} zł.", discord.Color.gold()))
            return
        cur.execute("UPDATE players SET gold = gold - ? WHERE user_id=?", (price, interaction.user.id))
        add_item(interaction.user.id, item_id, qty)
        conn.commit()
        await interaction.response.send_message(embed=make_embed("🛒 Zakup zakończony", f"Kupiłeś {it['name']} x{qty} za {price} zł.", discord.Color.gold()))

    @app_commands.command(name="trening", description="🏋️ Trenuj (+1 do wybranego statu za złoto)")
    @app_commands.describe(stat="Wybierz: strength/dexterity/wisdom/charisma")
    async def trening(self, interaction: discord.Interaction, stat: str):
        create_player(interaction.user)
        if stat not in ("strength","dexterity","wisdom","charisma"):
            await interaction.response.send_message(embed=make_embed("❌ Nieprawidłowy stat", "Wybierz: strength/dexterity/wisdom/charisma", discord.Color.blue()))
            return
        cost = 50
        p = get_player(interaction.user.id)
        if p["gold"] < cost:
            await interaction.response.send_message(embed=make_embed("❌ Za mało złota", f"Potrzebujesz {cost} zł.", discord.Color.blue()))
            return
        cur = conn.cursor()
        cur.execute(f"UPDATE players SET {stat} = {stat} + 1, gold = gold - ? WHERE user_id=?", (cost, interaction.user.id))
        conn.commit()
        await interaction.response.send_message(embed=make_embed("🏋️ Trening", f"Zwiększono {stat} o 1 za {cost} zł.", discord.Color.blue()))

    @app_commands.command(name="misja", description="⚔️ Wybierz misję PvE")
    async def misja(self, interaction: discord.Interaction):
        create_player(interaction.user)
        p = get_player(interaction.user.id)
        uid = interaction.user.id
        enemy_lvl = max(1, p["lvl"] + random.randint(-1,2))
        enemy_hp = 30 + enemy_lvl*10
        player_hp = p["hp"]
        rounds=[]
        atk = p["strength"] + int(p["dexterity"]/2)
        while enemy_hp > 0 and player_hp > 0:
            dmg = max(1, atk//4 + random.randint(0,6))
            enemy_hp -= dmg
            rounds.append(f"Ty zadajesz {dmg} obrażeń. (enemy {max(0,enemy_hp)})")
            if enemy_hp<=0: break
            edmg = random.randint(5,12) + enemy_lvl
            player_hp -= edmg
            rounds.append(f"Wrog zadaje {edmg} obrażeń. (ty {max(0,player_hp)})")
        if player_hp > 0:
            gold_gain = int(50 + p["lvl"]*5 + random.randint(0,30))
            xp_gain = 20 + enemy_lvl*5
            cur = conn.cursor()
            cur.execute("UPDATE players SET gold = gold + ?, xp = xp + ? WHERE user_id=?", (gold_gain, xp_gain, uid))
            # loot roll
            roll = random.randint(1,100)
            loot_msg = "Loot: złoto."
            if roll <= 20:
                add_item(uid, "potion_small", 1)
                loot_msg = "Loot: mikstura."
            elif roll <= 28:
                add_item(uid, "sword_wood",1)
                loot_msg = "Loot: przedmiot."
            elif roll <= 30:
                add_item(uid, "crown_atlantyda",1)
                loot_msg = "Loot: artefakt!"
            conn.commit()
            e = make_embed("🏆 Misja ukończona!", f"Zdobyłeś {gold_gain} złota i {xp_gain} XP.\n{loot_msg}", discord.Color.red())
            e.add_field(name="Przebieg", value="\\n".join(rounds[:8]) + ("\\n..." if len(rounds)>8 else ""))
            await interaction.response.send_message(embed=e)
        else:
            loss = min(p["gold"], 20)
            cur = conn.cursor()
            cur.execute("UPDATE players SET gold = gold - ? WHERE user_id=?", (loss, uid))
            conn.commit()
            e = make_embed("💀 Porażka", f"Twój bohater został pokonany. Straciłeś {loss} złota.", discord.Color.red())
            e.add_field(name="Przebieg", value="\\n".join(rounds[:8]) + ("\\n..." if len(rounds)>8 else ""))
            await interaction.response.send_message(embed=e)

    @app_commands.command(name="pojedynki", description="⚔️ Wyzwij gracza na pojedynek")
    @app_commands.describe(opponent="Wybierz przeciwnika")
    async def pojedynki(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            await interaction.response.send_message(embed=make_embed("❌ Nie można walczyć z botem", "", discord.Color.red()))
            return
        create_player(interaction.user)
        create_player(opponent)
        p1 = get_player(interaction.user.id)
        p2 = get_player(opponent.id)
        hp1 = p1["hp"]; hp2 = p2["hp"]
        atk1 = p1["strength"] + int(p1["dexterity"]/2)
        atk2 = p2["strength"] + int(p2["dexterity"]/2)
        rounds=[]
        while hp1>0 and hp2>0:
            d1 = max(1, atk1//4 + random.randint(0,6))
            hp2 -= d1
            rounds.append(f"{interaction.user.display_name} zadaje {d1} obrażeń.")
            if hp2<=0: break
            d2 = max(1, atk2//4 + random.randint(0,6))
            hp1 -= d2
            rounds.append(f"{opponent.display_name} zadaje {d2} obrażeń.")
        if hp1>0:
            winner = interaction.user
            loser = opponent
        else:
            winner = opponent
            loser = interaction.user
        cur = conn.cursor()
        cur.execute("UPDATE players SET xp = xp + ? WHERE user_id=?", (30, winner.id))
        roll = random.randint(1,100)
        loot_msg = ""
        if roll <= 5:
            add_item(winner.id, "blade_victory",1)
            loot_msg = " Znalazłeś unikat: Ostrze zwycięzcy!"
        conn.commit()
        e = make_embed("⚔️ Pojedynek zakończony", f"Zwycięzca: {winner.display_name}.{loot_msg}", discord.Color.red())
        e.add_field(name="Przebieg", value="\\n".join(rounds[:8]) + ("\\n..." if len(rounds)>8 else ""))
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="handel", description="🔁 Wymiana z graczem (prośba)")
    @app_commands.describe(target="Gracz", your_item="Twój item_id", their_item="Proszony item_id")
    async def handel(self, interaction: discord.Interaction, target: discord.Member, your_item: str, their_item: str):
        if target.bot:
            await interaction.response.send_message(embed=make_embed("❌ Nie można handlować z botem","", discord.Color.gold()))
            return
        create_player(interaction.user); create_player(target)
        e = make_embed("🔁 Prośba o wymianę", f"{interaction.user.mention} prosi {target.mention} o wymianę: `{your_item}` ⇄ `{their_item}`", discord.Color.gold())
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="gildia", description="🏰 Komendy gildii: stwórz/dołącz/opuść/info/wojna/ranking")
    @app_commands.describe(action="stwórz/dołącz/opuść/info/wojna/ranking", name="Nazwa gildii (przy stwórz/wojna)")
    async def gildia(self, interaction: discord.Interaction, action: str, name: str = ""):
        create_player(interaction.user)
        cur = conn.cursor()
        uid = interaction.user.id
        if action == "stwórz":
            cost = 500
            p = get_player(uid)
            if p["gold"] < cost:
                await interaction.response.send_message(embed=make_embed("❌ Za mało złota", f"Koszt: {cost} zł.", discord.Color.green()))
                return
            try:
                cur.execute("INSERT INTO guilds (name, owner_id, members) VALUES (?, ?, ?)", (name, uid, json.dumps([uid])))
                cur.execute("UPDATE players SET gold = gold - ? WHERE user_id=?", (cost, uid))
                conn.commit()
                await interaction.response.send_message(embed=make_embed("✅ Gildia założona", f"Stworzono {name}", discord.Color.green()))
            except Exception as e:
                await interaction.response.send_message(embed=make_embed("❌ Błąd", str(e), discord.Color.green()))
        elif action == "dołącz":
            cur.execute("SELECT * FROM guilds WHERE name=?", (name,))
            g = cur.fetchone()
            if not g:
                await interaction.response.send_message(embed=make_embed("❌ Nie znaleziono gildii", "", discord.Color.green()))
                return
            members = json.loads(g["members"])
            if uid in members:
                await interaction.response.send_message(embed=make_embed("ℹ️ Jesteś już w gildii", "", discord.Color.green()))
                return
            members.append(uid)
            cur.execute("UPDATE guilds SET members=? WHERE id=?", (json.dumps(members), g["id"]))
            conn.commit()
            await interaction.response.send_message(embed=make_embed("✅ Dołączono", f"Dołączyłeś do gildii {name}", discord.Color.green()))
        elif action == "opuść":
            cur.execute("SELECT * FROM guilds WHERE members LIKE ?", ('%'+str(uid)+'%',))
            g = None
            for row in cur.fetchall():
                members = json.loads(row["members"])
                if uid in members:
                    g = row; break
            if not g:
                await interaction.response.send_message(embed=make_embed("ℹ️ Nie jesteś w żadnej gildii", "", discord.Color.green()))
                return
            members = json.loads(g["members"]); members.remove(uid)
            cur.execute("UPDATE guilds SET members=? WHERE id=?", (json.dumps(members), g["id"]))
            conn.commit()
            await interaction.response.send_message(embed=make_embed("✅ Opuściłeś gildii", f"Opuszczono {g['name']}", discord.Color.green()))
        elif action == "info":
            cur.execute("SELECT * FROM guilds WHERE name=?", (name,))
            g = cur.fetchone()
            if not g:
                await interaction.response.send_message(embed=make_embed("❌ Nie znaleziono gildii", "", discord.Color.green()))
                return
            members = json.loads(g["members"])
            await interaction.response.send_message(embed=make_embed(f"🏰 Gildia — {g['name']}", f"Właściciel: <@{g['owner_id']}> | Członków: {len(members)} | Prestiż: {g['prestige']}", discord.Color.green()))
        elif action == "wojna":
            cur.execute("SELECT * FROM guilds WHERE members LIKE ?", ('%'+str(uid)+'%',))
            myg = None
            for row in cur.fetchall():
                members = json.loads(row["members"])
                if uid in members:
                    myg = row; break
            if not myg:
                await interaction.response.send_message(embed=make_embed("❌ Nie jesteś w gildii", "", discord.Color.green()))
                return
            cur.execute("SELECT * FROM guilds WHERE name=?", (name,))
            other = cur.fetchone()
            if not other:
                await interaction.response.send_message(embed=make_embed("❌ Nie znaleziono gildii", "", discord.Color.green()))
                return
            now = int(time.time()); end = now + 3*24*3600
            cur.execute("INSERT INTO wars (guild_a, guild_b, start_ts, end_ts, active) VALUES (?,?,?,?,1)", (myg["name"], other["name"], now, end))
            conn.commit()
            await interaction.response.send_message(embed=make_embed("⚔️ Wojna rozpoczęta", f"Wojna między {myg['name']} a {other['name']} potrwa 3 dni.", discord.Color.green()))
        elif action == "ranking":
            cur.execute("SELECT name, prestige FROM guilds ORDER BY prestige DESC LIMIT 10")
            rows = cur.fetchall()
            desc = "\\n".join([f"{idx+1}. {r['name']} — Prestiż: {r['prestige']}" for idx, r in enumerate(rows)])
            await interaction.response.send_message(embed=make_embed("🏆 Ranking gildii", desc or "Brak gildii", discord.Color.green()))
        else:
            await interaction.response.send_message(embed=make_embed("❌ Nieznana akcja", "Użyj: stwórz/dołącz/opuść/info/wojna/ranking", discord.Color.green()))

    @app_commands.command(name="ranking", description="🏅 TOP gracze")
    async def ranking(self, interaction: discord.Interaction):
        cur = conn.cursor()
        cur.execute("SELECT name, lvl, xp FROM players ORDER BY lvl DESC, xp DESC LIMIT 10")
        rows = cur.fetchall()
        desc = "\\n".join([f"{idx+1}. {r['name']} — Poziom: {r['lvl']}" for idx,r in enumerate(rows)])
        await interaction.response.send_message(embed=make_embed("🏅 TOP Graczy", desc or "Brak danych", discord.Color.purple()))

    @app_commands.command(name="admin", description="👑 Admin actions")
    @app_commands.describe(action="reset/give/block/event", target="@gracz", field="xp/gold/item", value="amount or item_id", text="event description")
    async def admin(self, interaction: discord.Interaction, action: str, target: discord.Member = None, field: str = "", value: str = "", text: str = ""):
        owner = int((interaction.client.bot_owner if hasattr(interaction.client, 'bot_owner') else 0) or 0)
        # simplified check: allow if guild admin or owner env var set (owner in .env not accessible here)
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == owner):
            await interaction.response.send_message(embed=make_embed("❌ Brak uprawnień", "", discord.Color.dark_grey()))
            return
        cur = conn.cursor()
        if action == "reset" and target:
            cur.execute("DELETE FROM players WHERE user_id=?", (target.id,))
            cur.execute("DELETE FROM inventory WHERE user_id=?", (target.id,))
            conn.commit()
            await interaction.response.send_message(embed=make_embed("🔄 Reset", f"Zresetowano postać {target.display_name}", discord.Color.dark_grey()))
        elif action == "give" and target and field:
            if field == "xp":
                cur.execute("UPDATE players SET xp = xp + ? WHERE user_id=?", (int(value), target.id))
            elif field == "gold":
                cur.execute("UPDATE players SET gold = gold + ? WHERE user_id=?", (int(value), target.id))
            elif field == "item":
                add_item(target.id, value, 1)
            conn.commit()
            await interaction.response.send_message(embed=make_embed("✅ Give", f"Dano {field} {value} do {target.display_name}", discord.Color.dark_grey()))
        elif action == "block" and target:
            await interaction.response.send_message(embed=make_embed("⛔ Block", f"Zablokowano {target.display_name} (demo)", discord.Color.dark_grey()))
        elif action == "event":
            await interaction.response.send_message(embed=make_embed("📣 Event", f"Ogłoszenie: {text}", discord.Color.dark_grey()))
        else:
            await interaction.response.send_message(embed=make_embed("❌ Nieznana komenda admin", "", discord.Color.dark_grey()))

    @tasks.loop(minutes=30)
    async def war_task(self):
        cur = conn.cursor()
        now = int(time.time())
        cur.execute("SELECT * FROM wars WHERE active=1 AND end_ts<=?", (now,))
        rows = cur.fetchall()
        for w in rows:
            score_a = random.randint(0,500)
            score_b = random.randint(0,500)
            if score_a>score_b:
                cur.execute("UPDATE guilds SET prestige = prestige + 100 WHERE name=?", (w["guild_a"],))
            elif score_b>score_a:
                cur.execute("UPDATE guilds SET prestige = prestige + 100 WHERE name=?", (w["guild_b"],))
            cur.execute("UPDATE wars SET active=0, score_a=?, score_b=? WHERE id=?", (score_a, score_b, w["id"]))
        conn.commit()

async def setup(bot):
    await bot.add_cog(RPG(bot))
