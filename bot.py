import discord
from discord.ext import commands
import os, asyncio, time
from dotenv import load_dotenv
import db_pg

load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)


# ====== EVENTY ======
@bot.event
async def on_ready():
    print(f"🌊 Atlantyda RPG uruchomiona jako {bot.user}")
    await db_pg.init_db()
    print("📦 Połączono z bazą danych i zainicjowano tabele.")
    synced = await bot.tree.sync()
    print(f"✅ Zsynchronizowano {len(synced)} komend slash.")


# ====== KOMENDY RPG ======
@bot.tree.command(name="start", description="Rozpocznij grę w Atlantydzie")
async def start(interaction: discord.Interaction, klasa: str):
    user = interaction.user
    existing = await db_pg.get_player(user.id)
    if existing:
        await interaction.response.send_message("🧙 Już masz postać! Użyj /profil.", ephemeral=True)
        return

    klasy = {
        "wojownik": {"str": 5, "dex": 2, "wis": 1, "cha": 1, "hp_bonus": 15},
        "mag": {"str": 1, "dex": 2, "wis": 6, "cha": 1, "hp_bonus": 5},
        "złodziej": {"str": 2, "dex": 6, "wis": 2, "cha": 2, "hp_bonus": 10},
        "paladyn": {"str": 3, "dex": 2, "wis": 3, "cha": 3, "hp_bonus": 12},
    }

    if klasa.lower() not in klasy:
        await interaction.response.send_message("⚔️ Klasy: Wojownik, Mag, Złodziej, Paladyn.", ephemeral=True)
        return

    stats = klasy[klasa.lower()]
    await db_pg.create_player(user.id, user.name, klasa.capitalize(), stats)
    await interaction.response.send_message(f"🎉 Stworzyłeś postać **{klasa.capitalize()}**!")


@bot.tree.command(name="profil", description="Zobacz profil swojej postaci")
async def profil(interaction: discord.Interaction):
    user = interaction.user
    player = await db_pg.get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ Nie masz postaci. Użyj /start.", ephemeral=True)
        return

    embed = discord.Embed(title=f"🏰 {player['name']} — {player['class']}", color=discord.Color.blue())
    embed.add_field(name="Poziom", value=player['level'])
    embed.add_field(name="XP", value=player['xp'])
    embed.add_field(name="HP", value=f"{player['hp']}/{player['max_hp']}")
    embed.add_field(name="Złoto", value=player['gold'])
    embed.add_field(name="Statystyki",
                    value=f"STR: {player['str']}\nDEX: {player['dex']}\nWIS: {player['wis']}\nCHA: {player['cha']}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ekwipunek", description="Zobacz swój ekwipunek")
async def ekwipunek(interaction: discord.Interaction):
    user = interaction.user
    items = await db_pg.get_inventory(user.id)
    if not items:
        await interaction.response.send_message("🎒 Twój ekwipunek jest pusty.", ephemeral=True)
        return

    text = "\n".join([f"• {i['item_id']} x{i['qty']}" for i in items])
    embed = discord.Embed(title=f"Ekwipunek {user.name}", description=text, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ranking", description="Zobacz ranking graczy według poziomu")
async def ranking(interaction: discord.Interaction):
    pool = await db_pg.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT name, level, xp FROM players ORDER BY level DESC, xp DESC LIMIT 10")
    if not rows:
        await interaction.response.send_message("🏅 Brak danych w rankingu.")
        return
    text = "\n".join([f"**{i+1}.** {r['name']} — Lv {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows)])
    embed = discord.Embed(title="🏆 Ranking Atlantydy", description=text, color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)


# ====== GILDIE ======
@bot.tree.command(name="stworz_gildie", description="Stwórz nową gildię")
async def stworz_gildie(interaction: discord.Interaction, nazwa: str):
    user = interaction.user
    player = await db_pg.get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ Najpierw stwórz postać (/start).", ephemeral=True)
        return
    existing = await db_pg.get_player_guild(user.id)
    if existing:
        await interaction.response.send_message("🛡️ Już jesteś w gildii!", ephemeral=True)
        return
    try:
        gid = await db_pg.create_guild(nazwa, user.id)
        await interaction.response.send_message(f"🏰 Gildia **{nazwa}** została utworzona! Jesteś jej mistrzem.")
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Nie udało się stworzyć gildii: {e}", ephemeral=True)


@bot.tree.command(name="dolacz", description="Dołącz do istniejącej gildii")
async def dolacz(interaction: discord.Interaction, nazwa: str):
    user = interaction.user
    guild = await db_pg.get_guild_by_name(nazwa)
    if not guild:
        await interaction.response.send_message("❌ Nie znaleziono takiej gildii.", ephemeral=True)
        return
    await db_pg.join_guild(guild['id'], user.id)
    await interaction.response.send_message(f"🤝 Dołączyłeś do gildii **{guild['name']}**!")


@bot.tree.command(name="gildia", description="Zobacz informacje o swojej gildii")
async def gildia(interaction: discord.Interaction):
    user = interaction.user
    membership = await db_pg.get_player_guild(user.id)
    if not membership:
        await interaction.response.send_message("🏕️ Nie należysz do żadnej gildii.", ephemeral=True)
        return
    guild = await db_pg.get_guild_by_id(membership['guild_id'])
    embed = discord.Embed(title=f"🏰 {guild['name']}", color=discord.Color.green())
    embed.add_field(name="Mistrz", value=f"<@{guild['leader']}>")
    embed.add_field(name="Prestiż", value=guild['prestige'])
    embed.add_field(name="Liczba członków", value=guild['members_count'])
    await interaction.response.send_message(embed=embed)


# ====== WOJNY ======
@bot.tree.command(name="rozpocznij_wojne", description="Rozpocznij wojnę między gildiami")
async def rozpocznij_wojne(interaction: discord.Interaction, gildia_a: str, gildia_b: str):
    g1 = await db_pg.get_guild_by_name(gildia_a)
    g2 = await db_pg.get_guild_by_name(gildia_b)
    if not g1 or not g2:
        await interaction.response.send_message("❌ Jedna z gildii nie istnieje.", ephemeral=True)
        return
    start_ts = int(time.time())
    end_ts = start_ts + 3600 * 24
    war_id = await db_pg.create_war(g1["id"], g2["id"], start_ts, end_ts)
    await interaction.response.send_message(f"⚔️ Rozpoczęto wojnę między **{gildia_a}** a **{gildia_b}**! (ID: {war_id})")


@bot.tree.command(name="aktywn_wojny", description="Zobacz trwające wojny")
async def aktywn_wojny(interaction: discord.Interaction):
    wars = await db_pg.get_active_wars()
    if not wars:
        await interaction.response.send_message("🕊️ Brak aktywnych wojen.")
        return
    text = "\n".join([f"⚔️ {w['guild_a']} vs {w['guild_b']} (ID: {w['id']})" for w in wars])
    await interaction.response.send_message(text)


# ====== PANEL ADMINA ======
@bot.tree.command(name="panel_admina", description="Panel administratora RPG (tylko właściciel)")
@commands.is_owner()
async def panel_admina(interaction: discord.Interaction):
    embed = discord.Embed(title="⚙️ Panel Administratora", color=discord.Color.red())
    embed.add_field(name="/dodaj_item", value="Dodaj przedmiot graczowi", inline=False)
    embed.add_field(name="/rozpocznij_wojne", value="Rozpocznij wojnę między gildiami", inline=False)
    embed.add_field(name="/ranking", value="Zobacz ranking graczy", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="dodaj_item", description="Dodaj przedmiot graczowi (Admin)")
@commands.is_owner()
async def dodaj_item(interaction: discord.Interaction, user: discord.User, item: str, ilosc: int = 1):
    await db_pg.add_item(user.id, item, ilosc)
    await interaction.response.send_message(f"🎁 Dodano {ilosc}x {item} do {user.name}")


# ====== START ======
async def main():
    async with bot:
        await bot.load_extension("guide")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
