import os
import asyncio
import time
import random
import logging
from typing import List, Tuple

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import db_pg      # musi mieć get_pool(), init_db(), get_player(), create_player(), update_player(), add_item(), get_inventory(), create_guild(), join_guild(), get_guild_by_name(), get_guild_by_id(), get_player_guild(), create_war(), get_active_wars(), increment_war_win(), end_war()
import items      # lista ITEMS = [{'id','name','price','level'}, ...]

load_dotenv()
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Basic checks
if not TOKEN:
    raise RuntimeError("Brak TOKEN w .env")
if not DATABASE_URL:
    # db_pg may also raise if missing - but warn now
    print("⚠️ Uwaga: brak DATABASE_URL w .env — upewnij się, że zmienna jest ustawiona w Railway.")

# Constants
ATLANTYDA_CHANNEL_ID = 1421188560165277776
OWNER_ID = 1388648862008344608

# Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("atlantyda")

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ---------------------------
# Helper utilities
# ---------------------------
def in_game_channel(channel: discord.abc.GuildChannel) -> bool:
    return channel is not None and channel.id == ATLANTYDA_CHANNEL_ID

def short_name(name: str, max_len: int = 40) -> str:
    return (name[:max_len-3] + "...") if len(name) > max_len else name

async def fetch_all_players() -> List[Tuple[int, str]]:
    pool = await db_pg.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, name FROM players")
    return [(r['user_id'], r['name']) for r in rows]

async def is_owner_or_admin(user: discord.User) -> bool:
    # owner or server admin anywhere
    try:
        app_info = await bot.application_info()
        if user.id == app_info.owner.id or user.id == OWNER_ID:
            return True
    except Exception:
        pass
    for g in bot.guilds:
        m = g.get_member(user.id)
        if m and (m.guild_permissions.administrator or m.guild_permissions.manage_guild):
            return True
    return False

# ---------------------------
# UI: Views / Selects / Modals
# ---------------------------

# --- MainPanelView: per-user ephemeral panel with buttons ---
class MainPanelView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int | None = None):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # only the user can interact with their panel
        if interaction.user.id != self.user_id and not await is_owner_or_admin(interaction.user):
            await interaction.response.send_message("To nie jest Twój panel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎮 Stwórz postać / Start", style=discord.ButtonStyle.primary, custom_id="btn_start")
    async def btn_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await db_pg.get_player(self.user_id)
        if player:
            return await interaction.response.send_message("Masz już postać — użyj 'Panel postaci'.", ephemeral=True)
        await interaction.response.send_message("Wybierz klasę:", view=ClassSelectView(self.user_id), ephemeral=True)

    @discord.ui.button(label="🧾 Panel postaci", style=discord.ButtonStyle.secondary, custom_id="btn_profile")
    async def btn_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await db_pg.get_player(self.user_id)
        if not p:
            return await interaction.response.send_message("Nie masz postaci. Kliknij 'Stwórz postać'.", ephemeral=True)
        embed = discord.Embed(title=f"🌊 Panel — {p['name']}", color=discord.Color.blue())
        embed.add_field(name="Klasa", value=p['class'], inline=True)
        embed.add_field(name="Poziom", value=str(p['level']), inline=True)
        embed.add_field(name="XP", value=str(p['xp']), inline=True)
        embed.add_field(name="HP", value=f"{p['hp']}/{p['max_hp']}", inline=True)
        embed.add_field(name="Złoto", value=str(p['gold']), inline=True)
        embed.add_field(name="STR", value=str(p['str']), inline=True)
        embed.add_field(name="DEX", value=str(p['dex']), inline=True)
        embed.add_field(name="WIS", value=str(p['wis']), inline=True)
        embed.add_field(name="CHA", value=str(p['cha']), inline=True)
        inv = await db_pg.get_inventory(self.user_id)
        inv_text = ", ".join([f"{i['item_id']} x{i['qty']}" for i in inv]) or "Brak"
        embed.add_field(name="Ekwipunek", value=inv_text[:1000], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚔️ PvE", style=discord.ButtonStyle.success, custom_id="btn_pve")
    async def btn_pve(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await db_pg.get_player(self.user_id)
        if not p:
            return await interaction.response.send_message("Nie masz postaci.", ephemeral=True)
        embed = await handle_pve(p)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🤺 PvP", style=discord.ButtonStyle.danger, custom_id="btn_pvp")
    async def btn_pvp(self, interaction: discord.Interaction, button: discord.ui.Button):
        # show select of opponents
        rows = await fetch_all_players()
        options = [discord.SelectOption(label=short_name(name), value=str(uid)) for uid, name in rows if uid != self.user_id]
        if not options:
            return await interaction.response.send_message("Brak dostępnych przeciwników.", ephemeral=True)
        view = OpponentSelectView(self.user_id, options)
        await interaction.response.send_message("Wybierz przeciwnika do PvP:", view=view, ephemeral=True)

    @discord.ui.button(label="🏪 Sklep", style=discord.ButtonStyle.primary)
    async def btn_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        import items

        # Kategorie sklepu
        categories = {
            "Wojownik": [it for it in items.ITEMS if it["class"] == "Wojownik"],
            "Zabójca": [it for it in items.ITEMS if it["class"] == "Zabójca"],
            "Mag": [it for it in items.ITEMS if it["class"] == "Mag"],
            "Kapłan": [it for it in items.ITEMS if it["class"] == "Kapłan"],
            "Artefakty": [it for it in items.ITEMS if it["class"] == "All"],
        }

        # Tworzymy menu kategorii
        cat_options = [
            discord.SelectOption(label=name, value=name, description=f"Przedmioty klasy {name}")
            for name in categories.keys()
        ]

        class CategorySelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="Wybierz kategorię...", options=cat_options)

            async def callback(self, interaction: discord.Interaction):
                cat = self.values[0]
                items_list = categories[cat]

                # Podmenu z przedmiotami (max 25)
                item_options = [
                    discord.SelectOption(
                        label=f"{it['name']} — {it.get('price', '?')}💧 (lvl {it.get('level', 1)})",
                        description=f"+{it.get('hp',0)}HP +{it.get('str',0)}STR +{it.get('dex',0)}DEX +{it.get('wis',0)}WIS +{it.get('cha',0)}CHA",
                        value=it["id"]
                    )
                    for it in items_list[:25]
                ]

                class ItemSelect(discord.ui.Select):
                    def __init__(self):
                        super().__init__(placeholder=f"🛒 Wybierz przedmiot ({cat})", options=item_options)

                    async def callback(self, interaction: discord.Interaction):
                        item_id = self.values[0]
                        selected_item = next(it for it in items.ITEMS if it["id"] == item_id)

                        # Zapis zakupu
                        pool = await db_pg.get_pool()
                        player = await db_pg.get_player(pool, interaction.user.id)

                        if player["water"] < selected_item["price"]:
                            await interaction.response.send_message("❌ Nie masz wystarczająco 💧!", ephemeral=True)
                            return

                        await db_pg.add_item(pool, interaction.user.id, selected_item["id"])
                        await db_pg.update_player(pool, interaction.user.id, water=player["water"] - selected_item["price"])

                        await interaction.response.send_message(
                            f"✅ Kupiłeś **{selected_item['name']}** za {selected_item['price']}💧!",
                            ephemeral=True
                        )

                view = discord.ui.View()
                view.add_item(ItemSelect())
                await interaction.response.send_message(f"📜 Sklep — kategoria **{cat}**", view=view, ephemeral=True)

        view = discord.ui.View()
        view.add_item(CategorySelect())
        await interaction.response.send_message("🛍️ Wybierz kategorię sklepu:", view=view, ephemeral=True)

    @discord.ui.button(label="🏰 Gildia", style=discord.ButtonStyle.secondary, custom_id="btn_guild")
    async def btn_guild(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GuildActionView(self.user_id)
        await interaction.response.send_message("Akcje gildii:", view=view, ephemeral=True)

    @discord.ui.button(label="📊 Ranking", style=discord.ButtonStyle.secondary, custom_id="btn_rank")
    async def btn_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        pool = await db_pg.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT name, level, gold FROM players ORDER BY level DESC, gold DESC LIMIT 10")
        text = "\n".join([f"{i+1}. {r['name']} — lvl {r['level']} ({r['gold']}💧)" for i, r in enumerate(rows)]) or "Brak graczy"
        embed = discord.Embed(title="🏆 Ranking TOP10", description=text, color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚙️ Admin", style=discord.ButtonStyle.danger, custom_id="btn_admin")
    async def btn_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_owner_or_admin(interaction.user):
            return await interaction.response.send_message("Brak uprawnień admina.", ephemeral=True)
        await interaction.response.send_message("Panel administratora:", view=AdminPanelView(self.user_id), ephemeral=True)


# --- Class selection (Select inside View + callback that creates player) ---
class ClassSelectView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        options = [
            discord.SelectOption(label="Wojownik – wytrzymały", value="Wojownik", description="HP+15, STR+2"),
            discord.SelectOption(label="Zabójca – zwinny", value="Zabójca", description="DEX+3, STR+1"),
            discord.SelectOption(label="Mag – inteligentny", value="Mag", description="WIS+3, DEX+1"),
            discord.SelectOption(label="Kapłan – wspierający", value="Kapłan", description="WIS+2, CHA+2"),
        ]
        self.add_item(ClassSelect(options, user_id))

class ClassSelect(discord.ui.Select):
    def __init__(self, options, user_id):
        super().__init__(placeholder="Wybierz klasę...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój wybór.", ephemeral=True)
        choice = self.values[0]
        presets = {
            "Wojownik": {'str': 7, 'dex': 4, 'wis': 3, 'cha': 6, 'hp_bonus': 15},
            "Zabójca": {'str': 6, 'dex': 8, 'wis': 2, 'cha': 4, 'hp_bonus': 6},
            "Mag": {'str': 3, 'dex': 4, 'wis': 10, 'cha': 3, 'hp_bonus': 4},
            "Kapłan": {'str': 4, 'dex': 3, 'wis': 6, 'cha': 7, 'hp_bonus': 8},
        }
        stats = presets.get(choice, {'str':5,'dex':5,'wis':5,'cha':5,'hp_bonus':5})
        try:
            await db_pg.create_player(self.user_id, interaction.user.name, choice, stats, gold=200)
            await interaction.response.send_message(f"🎉 Stworzono postać **{choice}**!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd tworzenia postaci: {e}", ephemeral=True)

# --- Opponent select for PvP ---
class OpponentSelectView(discord.ui.View):
    def __init__(self, user_id: int, options: List[discord.SelectOption], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.add_item(OpponentSelect(options, user_id))

class OpponentSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], user_id: int):
        super().__init__(placeholder="Wybierz przeciwnika...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój wybór.", ephemeral=True)
        target_id = int(self.values[0])
        p1 = await db_pg.get_player(self.user_id)
        p2 = await db_pg.get_player(target_id)
        if not p1 or not p2:
            return await interaction.response.send_message("Problem: gracz nie istnieje.", ephemeral=True)
        rounds = 3; s1 = 0; s2 = 0; logs = []
        for r in range(rounds):
            r1 = random.randint(1,20) + p1['str'] + p1['dex']
            r2 = random.randint(1,20) + p2['str'] + p2['dex']
            if r1 >= r2:
                s1 += 1; logs.append(f'R{r+1}: {p1["name"]} ({r1}) > {p2["name"]} ({r2})')
            else:
                s2 += 1; logs.append(f'R{r+1}: {p2["name"]} ({r2}) > {p1["name"]} ({r1})')
        if s1 > s2:
            await db_pg.update_player(self.user_id, gold=p1['gold'] + 10, xp=p1['xp'] + 5)
            result = f'🏆 {p1["name"]} wygrał PvP!'
        else:
            await db_pg.update_player(target_id, gold=p2['gold'] + 10, xp=p2['xp'] + 5)
            result = f'🏆 {p2["name"]} wygrał PvP!'
        embed = discord.Embed(title="🤺 PvP", description=result, color=discord.Color.gold())
        embed.add_field(name="Log", value="\n".join(logs[-6:])[:1900])
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Shop select ---
class ShopSelectView(discord.ui.View):
    def __init__(self, user_id: int, options: List[discord.SelectOption], timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.add_item(ShopSelect(options, user_id))

class ShopSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], user_id: int):
        super().__init__(placeholder="Wybierz przedmiot...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój wybór.", ephemeral=True)
        item_id = self.values[0]
        item = next((it for it in items.ITEMS if it['id'] == item_id), None)
        if not item:
            return await interaction.response.send_message("Nie znaleziono przedmiotu.", ephemeral=True)
        player = await db_pg.get_player(self.user_id)
        if not player:
            return await interaction.response.send_message("Nie masz postaci.", ephemeral=True)
        if player['level'] < item.get('level', 1):
            return await interaction.response.send_message(f"Potrzebujesz poziomu {item.get('level',1)}.", ephemeral=True)
        if player['gold'] < item.get('price', 999999):
            return await interaction.response.send_message("Nie masz wystarczająco złota.", ephemeral=True)
        await db_pg.update_player(self.user_id, gold=player['gold'] - item['price'])
        await db_pg.add_item(self.user_id, item_id)
        await interaction.response.send_message(f"✅ Kupiono {item['name']} za {item['price']}💧", ephemeral=True)

# --- Guild action view (create/join/info) ---
class GuildActionView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.add_item(GuildActionSelect(user_id))

class GuildActionSelect(discord.ui.Select):
    def __init__(self, user_id: int):
        options = [
            discord.SelectOption(label="Stwórz gildię", value="create", description="Utwórz nową gildię"),
            discord.SelectOption(label="Dołącz do gildii", value="join", description="Dołącz do istniejącej gildii"),
            discord.SelectOption(label="Informacje o mojej gildii", value="info", description="Zobacz szczegóły"),
        ]
        super().__init__(placeholder="Wybierz akcję gildii...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój wybór.", ephemeral=True)
        v = self.values[0]
        if v == "create":
            await interaction.response.send_modal(CreateGuildModal(self.user_id))
        elif v == "join":
            pool = await db_pg.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT id, name FROM guilds ORDER BY name")
            opts = [discord.SelectOption(label=r['name'], value=str(r['id'])) for r in rows]
            if not opts:
                return await interaction.response.send_message("Brak gildii do dołączenia.", ephemeral=True)
            await interaction.response.send_message("Wybierz gildii:", view=GuildJoinView(self.user_id, opts), ephemeral=True)
        else:
            ginfo = await db_pg.get_player_guild(self.user_id)
            if not ginfo:
                return await interaction.response.send_message("Nie należysz do żadnej gildii.", ephemeral=True)
            guild = await db_pg.get_guild_by_id(ginfo['guild_id'])
            embed = discord.Embed(title=f"🏰 {guild['name']}", color=discord.Color.green())
            embed.add_field(name="Mistrz", value=f"<@{guild['leader']}>")
            embed.add_field(name="Prestiż", value=guild['prestige'])
            embed.add_field(name="Członkowie", value=guild['members_count'])
            await interaction.response.send_message(embed=embed, ephemeral=True)

class CreateGuildModal(discord.ui.Modal, title="Stwórz gildię"):
    name = discord.ui.TextInput(label="Nazwa gildii", placeholder="Podaj nazwę gildii", max_length=32)
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            gid = await db_pg.create_guild(self.name.value.strip(), self.user_id)
            await interaction.response.send_message(f"🏰 Stworzono gildię {self.name.value} (ID {gid})", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)

class GuildJoinView(discord.ui.View):
    def __init__(self, user_id: int, options: List[discord.SelectOption], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.add_item(GuildJoinSelect(options, user_id))

class GuildJoinSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], user_id: int):
        super().__init__(placeholder="Wybierz gildię...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój wybór.", ephemeral=True)
        gid = int(self.values[0])
        await db_pg.join_guild(gid, self.user_id)
        await interaction.response.send_message("✅ Dołączono do gildii.", ephemeral=True)

# --- Admin panel UI ---
class AdminPanelView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int | None = None):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_owner_or_admin(interaction.user):
            await interaction.response.send_message("Brak uprawnień.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="➕ Dodaj złoto", style=discord.ButtonStyle.success)
    async def add_gold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddGoldModal())

    @discord.ui.button(label="🎁 Przyznaj przedmiot", style=discord.ButtonStyle.primary)
    async def grant_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = [discord.SelectOption(label=f"{it['name']} ({it['id']})", value=it['id']) for it in items.ITEMS]
        await interaction.response.send_message("Wybierz przedmiot:", view=AdminItemGrantView(options), ephemeral=True)

    @discord.ui.button(label="📢 Ogłoś event", style=discord.ButtonStyle.danger)
    async def announce_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EventModal())

class AddGoldModal(discord.ui.Modal, title="Dodaj złoto graczowi"):
    target = discord.ui.TextInput(label="Discord ID gracza")
    amount = discord.ui.TextInput(label="Ilość złota")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tid = int(self.target.value.strip())
            amt = int(self.amount.value.strip())
            p = await db_pg.get_player(tid)
            if not p:
                return await interaction.response.send_message("Użytkownik nie ma postaci.", ephemeral=True)
            await db_pg.update_player(tid, gold=p['gold'] + amt)
            await interaction.response.send_message(f"✅ Dodano {amt}💧 graczowi {p['name']}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)

class AdminItemGrantView(discord.ui.View):
    def __init__(self, options: List[discord.SelectOption], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.add_item(AdminItemSelect(options))

class AdminItemSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Wybierz item...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        await interaction.response.send_modal(AdminGrantModal(item_id))

class AdminGrantModal(discord.ui.Modal):
    def __init__(self, item_id: str):
        super().__init__(title="Przyznaj przedmiot")
        self.item_id = item_id
        self.target = discord.ui.TextInput(label="Discord ID gracza")
        self.add_item(self.target)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tid = int(self.target.value.strip())
            await db_pg.add_item(tid, self.item_id)
            await interaction.response.send_message("✅ Przedmiot przyznany.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)

class EventModal(discord.ui.Modal, title="Ogłoś event"):
    text = discord.ui.TextInput(label="Opis eventu", style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        ch = bot.get_channel(ATLANTYDA_CHANNEL_ID)
        if ch:
            await ch.send(f"🔥 EVENT: {self.text.value}")
            await interaction.response.send_message("Event ogłoszony.", ephemeral=True)
        else:
            await interaction.response.send_message("Kanał eventowy nie został znaleziony.", ephemeral=True)

# ---------------------------
# Gameplay logic functions
# ---------------------------
async def handle_pve(player: dict) -> discord.Embed:
    lvl = player['level']
    enemy_hp = 20 + lvl * 6 + random.randint(0, 8)
    enemy_atk = 2 + lvl + random.randint(0, 3)
    p_hp = player['hp']
    e_hp = enemy_hp
    log = []

    while p_hp > 0 and e_hp > 0:
        dmg = max(1, player['str'] + random.randint(1, 6))
        e_hp -= dmg
        log.append(f"Zadajesz {dmg}. Enemy HP {max(0, e_hp)}")
        if e_hp <= 0:
            break
        ed = max(1, enemy_atk + random.randint(0, 4))
        p_hp -= ed
        log.append(f"Wróg zadaje {ed}. Twoje HP {max(0, p_hp)}")

    if p_hp > 0:
        gold = 25 + lvl * 7
        xp = 15 + lvl * 3
        await db_pg.update_player(player['user_id'], gold=player['gold'] + gold, xp=player['xp'] + xp, hp=p_hp)
        loot_msg = ""
        if random.random() < 0.25:
            it = random.choice(items.ITEMS)
            await db_pg.add_item(player['user_id'], it['id'])
            loot_msg = f"Zdobyłeś: **{it['name']}**"
        embed = discord.Embed(title="⚔️ PvE — Zwycięstwo!", color=discord.Color.green())
        embed.add_field(name="Nagroda", value=f"+{gold}💧, +{xp} XP", inline=False)
        if loot_msg:
            embed.add_field(name="Loot", value=loot_msg, inline=False)
        embed.add_field(name="Log (ostatnie)", value="\n".join(log[-6:])[:1900], inline=False)
    else:
        await db_pg.update_player(player['user_id'], hp=1)
        embed = discord.Embed(title="💀 PvE — Porażka", description="Zostałeś pokonany. Odrodzisz się z 1 HP.", color=discord.Color.dark_gray())
        embed.add_field(name="Log", value="\n".join(log[-6:])[:1900], inline=False)

    return embed

# ---------------------------
# Background tasks: war monitor + events + panel sender
# ---------------------------
@tasks.loop(seconds=60)
async def war_monitor_task():
    now = int(time.time())
    try:
        wars = await db_pg.get_active_wars(now)
        ch = bot.get_channel(ATLANTYDA_CHANNEL_ID)
        for w in wars:
            if w['end_ts'] <= now:
                res = await db_pg.end_war(w['id'])
                if ch:
                    if res and res.get('winner'):
                        gw = await db_pg.get_guild_by_id(res['winner'])
                        embed = discord.Embed(title="🏁 Wojna zakończona", description=f"Zwycięzca: **{gw['name']}**", color=discord.Color.gold())
                        embed.add_field(name="Wynik", value=f"{res['wins'][0]} - {res['wins'][1]}")
                        await ch.send(embed=embed)
                    else:
                        await ch.send("🏁 Wojna zakończona remisem.")
    except Exception as e:
        log.exception("Błąd war_monitor_task: %s", e)

@tasks.loop(hours=1)
async def hourly_event_task():
    try:
        events = [
            ("🌑 Atak Cieni", "PvE +20% trudności"),
            ("🌊 Błogosławieństwo Posejdona", "Gildie w wojnie +1 pkt za PvP"),
            ("🔥 Magma", "Ataki magiczne +5 dmg")
        ]
        ev = random.choice(events)
        ch = bot.get_channel(ATLANTYDA_CHANNEL_ID)
        if ch:
            embed = discord.Embed(title="⏳ Event godzinowy", description=f"{ev[0]} — {ev[1]}", color=discord.Color.blue())
            await ch.send(embed=embed)
    except Exception as e:
        log.exception("Błąd hourly_event_task: %s", e)

async def send_start_panel_once():
    await bot.wait_until_ready()
    ch = bot.get_channel(ATLANTYDA_CHANNEL_ID)
    if not ch:
        log.warning("Nie znaleziono kanału startowego.")
        return
    embed = discord.Embed(title="🌊 Atlantyda RPG — Panel", description="Kliknij **Otwórz panel** aby sterować swoją postacią.", color=discord.Color.blurple())
    view = GlobalOpenPanelView()
    try:
        await ch.send(embed=embed, view=view)
    except Exception as e:
        log.exception("Błąd wysyłania startowego panelu: %s", e)

class GlobalOpenPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Otwórz panel", style=discord.ButtonStyle.primary)
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        mp = MainPanelView(interaction.user.id)
        embed = discord.Embed(title=f"🌊 Panel Gracza — {interaction.user.name}", description="Używaj przycisków aby sterować grą.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, view=mp, ephemeral=True)

# ---------------------------
# Bot events: ready/start
# ---------------------------
@bot.event
async def on_ready():
    log.info(f"🌊 Zalogowano jako {bot.user} (ID: {bot.user.id})")
    # init db
    try:
        await db_pg.init_db()
        log.info("🔗 Połączono i zainicjalizowano bazę danych.")
    except Exception as e:
        log.exception("Błąd init_db: %s", e)

    # sync app commands (so any app_commands are registered)
    try:
        synced = await bot.tree.sync()
        log.info(f"🔁 Zsynchronizowano {len(synced)} slash-komend.")
    except Exception as e:
        log.exception("Błąd synchronizacji slash-komend: %s", e)

    # start tasks
    if not war_monitor_task.is_running():
        war_monitor_task.start()
    if not hourly_event_task.is_running():
        hourly_event_task.start()
    # send start panel once
    bot.loop.create_task(send_start_panel_once())

# ---------------------------
# Minimal slash to open panel globally (optional)
# ---------------------------
@bot.tree.command(name="panel", description="Otwórz interaktywny panel Atlantyda RPG")
async def slash_panel(interaction: discord.Interaction):
    embed = discord.Embed(title=f"🌊 Panel Gracza — {interaction.user.name}", description="Używaj przycisków aby sterować grą.", color=discord.Color.blurple())
    view = MainPanelView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ---------------------------
# Startup helper + run
# ---------------------------
async def main():
    async with bot:
        # load cogs/extensions if you keep any
        try:
            await bot.load_extension("guide")
            log.info("Załadowano extension 'guide'.")
        except Exception:
            pass
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Wyłączono ręcznie.")
# ===============================
# 👑 PANEL ADMINA ATLANTYDY
# ===============================
import datetime

ADMIN_ID = 1388648862008344608  # ID właściciela bota

# --- Pomocnicze sprawdzenie uprawnień ---
async def is_owner_or_admin(user: discord.User) -> bool:
    if user.id == ADMIN_ID:
        return True
    member = getattr(user, "guild_permissions", None)
    return bool(member and member.administrator)


# --- Logowanie akcji adminów ---
async def log_admin_action(admin_id: int, action: str, details: str):
    pool = await db_pg.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id SERIAL PRIMARY KEY,
            admin_id BIGINT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        )
        """)
        await conn.execute(
            "INSERT INTO admin_logs (admin_id, action, details) VALUES ($1,$2,$3)",
            admin_id, action, details
        )


# --- Admin panel UI ---
class AdminPanelView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int | None = None):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_owner_or_admin(interaction.user):
            await interaction.response.send_message("Brak uprawnień.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="💰 Ekonomia", style=discord.ButtonStyle.success, row=0)
    async def economy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Panel ekonomii:", view=AdminEconomyView(), ephemeral=True)

    @discord.ui.button(label="🧙 Gracze", style=discord.ButtonStyle.primary, row=0)
    async def players(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Panel graczy:", view=AdminPlayerView(), ephemeral=True)

    @discord.ui.button(label="🏰 Gildie", style=discord.ButtonStyle.secondary, row=0)
    async def guilds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Panel gildii:", view=AdminGuildView(), ephemeral=True)

    @discord.ui.button(label="🎯 Poziomy", style=discord.ButtonStyle.danger, row=0)
    async def levels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Panel poziomów:", view=AdminLevelView(), ephemeral=True)


# --- Panel: Ekonomia ---
class AdminEconomyView(discord.ui.View):
    @discord.ui.button(label="➕ Dodaj złoto", style=discord.ButtonStyle.success)
    async def add_gold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddGoldModal())

    @discord.ui.button(label="🎁 Przyznaj przedmiot", style=discord.ButtonStyle.primary)
    async def grant_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = [discord.SelectOption(label=f"{it['name']} ({it['id']})", value=it['id']) for it in items.ITEMS]
        await interaction.response.send_message("Wybierz przedmiot:", view=AdminItemGrantView(options), ephemeral=True)


# --- Panel: Gracze ---
class AdminPlayerView(discord.ui.View):
    @discord.ui.button(label="❤️ Ulecz gracza", style=discord.ButtonStyle.success)
    async def heal_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(HealPlayerModal())

    @discord.ui.button(label="🚫 Zbanuj gracza (RPG)", style=discord.ButtonStyle.danger)
    async def ban_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BanPlayerModal())


# --- Panel: Gildie ---
class AdminGuildView(discord.ui.View):
    @discord.ui.button(label="⭐ Dodaj prestiż", style=discord.ButtonStyle.success)
    async def add_prestige(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddPrestigeModal())

    @discord.ui.button(label="🗑 Usuń gildię", style=discord.ButtonStyle.danger)
    async def delete_guild(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DeleteGuildModal())


# --- Panel: Poziomy i statystyki ---
class AdminLevelView(discord.ui.View):
    @discord.ui.button(label="📈 Dodaj poziom", style=discord.ButtonStyle.primary)
    async def add_level(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddLevelModal())

    @discord.ui.button(label="⚙️ Edytuj statystyki", style=discord.ButtonStyle.secondary)
    async def edit_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditStatsModal())


# -----------------------
# 🔧 Modalne okna admina
# -----------------------

class AddGoldModal(discord.ui.Modal, title="Dodaj złoto"):
    target = discord.ui.TextInput(label="ID gracza")
    amount = discord.ui.TextInput(label="Ilość złota")

    async def on_submit(self, interaction: discord.Interaction):
        tid = int(self.target.value.strip())
        amt = int(self.amount.value.strip())
        p = await db_pg.get_player(tid)
        if not p:
            return await interaction.response.send_message("❌ Gracz nie istnieje.", ephemeral=True)
        await db_pg.update_player(tid, gold=p['gold'] + amt)
        await log_admin_action(interaction.user.id, "Dodanie złota", f"Gracz {tid}, +{amt}💧")
        await interaction.response.send_message(f"✅ Dodano {amt}💧 graczowi {p['name']}.", ephemeral=True)


class HealPlayerModal(discord.ui.Modal, title="Ulecz gracza"):
    target = discord.ui.TextInput(label="ID gracza")
    async def on_submit(self, interaction: discord.Interaction):
        tid = int(self.target.value.strip())
        p = await db_pg.get_player(tid)
        if not p:
            return await interaction.response.send_message("Nie znaleziono gracza.", ephemeral=True)
        await db_pg.update_player(tid, hp=p['max_hp'])
        await log_admin_action(interaction.user.id, "Uleczenie gracza", f"Gracz {tid}")
        await interaction.response.send_message(f"✅ {p['name']} w pełni uleczony.", ephemeral=True)


class BanPlayerModal(discord.ui.Modal, title="Zbanuj gracza RPG"):
    target = discord.ui.TextInput(label="ID gracza")
    reason = discord.ui.TextInput(label="Powód bana", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        tid = int(self.target.value.strip())
        await db_pg.update_player(tid, banned=True)
        await log_admin_action(interaction.user.id, "Ban gracza", f"Gracz {tid}, powód: {self.reason.value}")
        await interaction.response.send_message(f"🚫 Zbanowano gracza ID {tid}. Powód: {self.reason.value}", ephemeral=True)


class AddPrestigeModal(discord.ui.Modal, title="Dodaj prestiż gildii"):
    guild_id = discord.ui.TextInput(label="ID gildii")
    amount = discord.ui.TextInput(label="Ilość prestiżu")
    async def on_submit(self, interaction: discord.Interaction):
        gid = int(self.guild_id.value.strip())
        amt = int(self.amount.value.strip())
        guild = await db_pg.get_guild_by_id(gid)
        if not guild:
            return await interaction.response.send_message("Nie znaleziono gildii.", ephemeral=True)
        new_prestige = guild["prestige"] + amt
        pool = await db_pg.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE guilds SET prestige=$1 WHERE id=$2", new_prestige, gid)
        await log_admin_action(interaction.user.id, "Dodanie prestiżu", f"Gildia {gid}, +{amt}")
        await interaction.response.send_message(f"⭐ Dodano {amt} prestiżu do {guild['name']}.", ephemeral=True)


class DeleteGuildModal(discord.ui.Modal, title="Usuń gildię"):
    guild_id = discord.ui.TextInput(label="ID gildii")
    async def on_submit(self, interaction: discord.Interaction):
        gid = int(self.guild_id.value.strip())
        pool = await db_pg.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM guilds WHERE id=$1", gid)
        await log_admin_action(interaction.user.id, "Usunięcie gildii", f"Gildia ID {gid}")
        await interaction.response.send_message(f"🗑 Usunięto gildię ID {gid}.", ephemeral=True)


class AddLevelModal(discord.ui.Modal, title="Dodaj poziom graczowi"):
    target = discord.ui.TextInput(label="ID gracza")
    amount = discord.ui.TextInput(label="Ilość poziomów")
    async def on_submit(self, interaction: discord.Interaction):
        tid = int(self.target.value.strip())
        amt = int(self.amount.value.strip())
        p = await db_pg.get_player(tid)
        if not p:
            return await interaction.response.send_message("Nie znaleziono gracza.", ephemeral=True)
        new_lvl = p['level'] + amt
        await db_pg.update_player(tid, level=new_lvl)
        await log_admin_action(interaction.user.id, "Dodanie poziomu", f"Gracz {tid}, +{amt} lvl")
        await interaction.response.send_message(f"📈 {p['name']} awansował do poziomu {new_lvl}.", ephemeral=True)


class EditStatsModal(discord.ui.Modal, title="Edytuj statystyki"):
    target = discord.ui.TextInput(label="ID gracza")
    str_val = discord.ui.TextInput(label="Siła (STR)", required=False, placeholder="np. 10")
    dex_val = discord.ui.TextInput(label="Zwinność (DEX)", required=False)
    wis_val = discord.ui.TextInput(label="Mądrość (WIS)", required=False)
    cha_val = discord.ui.TextInput(label="Charyzma (CHA)", required=False)
    hp_val = discord.ui.TextInput(label="HP", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        tid = int(self.target.value.strip())
        updates = {}
        for field in ["str_val", "dex_val", "wis_val", "cha_val", "hp_val"]:
            val = getattr(self, field).value.strip()
            if val:
                key = field.split("_")[0]
                updates[key] = int(val)
        if not updates:
            return await interaction.response.send_message("Brak zmian.", ephemeral=True)
        await db_pg.update_player(tid, **updates)
        await log_admin_action(interaction.user.id, "Edycja statystyk", f"Gracz {tid}, zmiany: {updates}")
        await interaction.response.send_message(f"✅ Zaktualizowano statystyki gracza {tid}.", ephemeral=True)


# --- Select: Przyznanie przedmiotu ---
class AdminItemGrantView(discord.ui.View):
    def __init__(self, options):
        super().__init__()
        self.add_item(discord.ui.Select(placeholder="Wybierz przedmiot", options=options))

    @discord.ui.select(placeholder="Wybierz przedmiot")
    async def select_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        await interaction.response.send_modal(GrantItemModal(item_id))


class GrantItemModal(discord.ui.Modal, title="Przyznaj przedmiot graczowi"):
    player_id = discord.ui.TextInput(label="ID gracza")
    qty = discord.ui.TextInput(label="Ilość", default="1")

    def __init__(self, item_id):
        super().__init__()
        self.item_id = item_id

    async def on_submit(self, interaction: discord.Interaction):
        pid = int(self.player_id.value.strip())
        qty = int(self.qty.value.strip())
        await db_pg.add_item(pid, self.item_id, qty)
        await log_admin_action(interaction.user.id, "Przyznanie przedmiotu", f"Gracz {pid}, przedmiot {self.item_id}, ilość {qty}")
        await interaction.response.send_message(f"🎁 Przyznano {qty}x {self.item_id} graczowi {pid}.", ephemeral=True)


# --- Komenda do otwierania panelu ---
@bot.slash_command(name="adminpanel", description="Otwiera panel administratora (dla właściciela lub admina)")
async def admin_panel(ctx: discord.ApplicationContext):
    if not await is_owner_or_admin(ctx.user):
        return await ctx.respond("🚫 Brak uprawnień.", ephemeral=True)
    await ctx.respond("👑 Panel administratora:", view=AdminPanelView(ctx.user.id), ephemeral=True)
