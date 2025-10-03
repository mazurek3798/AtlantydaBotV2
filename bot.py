import discord
from discord.ext import commands
import os, asyncio
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

# === EVENTY ===
@bot.event
async def on_ready():
    print(f"🌊 Atlantyda RPG uruchomiona jako {bot.user}")
    await db_pg.init_db()
    print("📦 Połączenie z bazą danych i inicjalizacja zakończona!")
    synced = await bot.tree.sync()
    print(f"✅ Zsynchronizowano {len(synced)} komend slash.")

# === PODSTAWOWE KOMENDY ===
@bot.tree.command(name="start", description="Rozpocznij grę w Atlantydzie")
async def start(interaction: discord.Interaction, klasa: str):
    user = interaction.user
    existing = await db_pg.get_player(user.id)
    if existing:
        await interaction.response.send_message("🧙 Już masz postać! Użyj /profil aby zobaczyć szczegóły.", ephemeral=True)
        return

    klasy = {
        "wojownik": {"str": 5, "dex": 2, "wis": 1, "cha": 1, "hp_bonus": 15},
        "mag": {"str": 1, "dex": 2, "wis": 6, "cha": 1, "hp_bonus": 5},
        "złodziej": {"str": 2, "dex": 6, "wis": 2, "cha": 2, "hp_bonus": 10},
        "paladyn": {"str": 3, "dex": 2, "wis": 3, "cha": 3, "hp_bonus": 12},
    }

    if klasa.lower() not in klasy:
        await interaction.response.send_message("⚔️ Dostępne klasy: Wojownik, Mag, Złodziej, Paladyn.", ephemeral=True)
        return

    stats = klasy[klasa.lower()]
    await db_pg.create_player(user.id, user.name, klasa.capitalize(), stats)
    await interaction.response.send_message(f"🎉 Stworzyłeś postać **{klasa.capitalize()}**! Powodzenia, {user.name}!")

@bot.tree.command(name="profil", description="Zobacz profil swojej postaci")
async def profil(interaction: discord.Interaction):
    user = interaction.user
    player = await db_pg.get_player(user.id)
    if not player:
        await interaction.response.send_message("❌ Nie masz jeszcze postaci. Użyj /start aby rozpocząć.", ephemeral=True)
        return

    embed = discord.Embed(title=f"🏰 Profil gracza {player['name']}", color=discord.Color.blue())
    embed.add_field(name="Klasa", value=player['class'], inline=True)
    embed.add_field(name="Poziom", value=player['level'], inline=True)
    embed.add_field(name="XP", value=player['xp'], inline=True)
    embed.add_field(name="HP", value=f"{player['hp']}/{player['max_hp']}", inline=True)
    embed.add_field(name="Złoto", value=player['gold'], inline=True)
    embed.add_field(name="Statystyki", 
                    value=f"STR: {player['str']}\nDEX: {player['dex']}\nWIS: {player['wis']}\nCHA: {player['cha']}", 
                    inline=False)
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

@bot.tree.command(name="dodaj_item", description="(Admin) Dodaj przedmiot graczowi")
@commands.is_owner()
async def dodaj_item(interaction: discord.Interaction, user: discord.User, item: str, ilosc: int = 1):
    await db_pg.add_item(user.id, item, ilosc)
    await interaction.response.send_message(f"🎁 Dodano {ilosc}x {item} do {user.name}")

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

# === ŁADOWANIE DODATKOWYCH MODUŁÓW ===
async def main():
    async with bot:
        await bot.load_extension("guide")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
