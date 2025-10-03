import discord, os, asyncio, time, random
from discord.ext import commands
from dotenv import load_dotenv
import db_pg, items

load_dotenv()

# === KONFIGURACJA ===
TOKEN = os.getenv("TOKEN")
ATLANTYDA_CHANNEL = int(os.getenv("ATLANTYDA_CHANNEL_ID") or 0)

# === INTENTY ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === FUNKCJE POMOCNICZE ===
def in_game_channel(ctx):
    return ctx.channel and ctx.channel.id == ATLANTYDA_CHANNEL

def format_remaining(end_ts):
    left = max(0, end_ts - int(time.time()))
    days = left // 86400
    hours = (left % 86400) // 3600
    mins = (left % 3600) // 60
    return f"{days}d {hours}h {mins}m" if left > 0 else "0m"

# === EVENT: BOT URUCHOMIONY ===
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

    # 🔹 Inicjalizacja bazy
    try:
        await db_pg.init_db()
        print("📦 Połączono z bazą danych i utworzono tabele (jeśli brakowało).")
    except Exception as e:
        print(f"❌ Błąd przy łączeniu z bazą danych: {e}")

    # 🔹 Uruchamiamy pętle eventów i wojen
    bot.loop.create_task(hourly_event_loop())
    bot.loop.create_task(war_monitor_loop())

    # 🔹 Ładujemy guide extension
    try:
        await bot.load_extension("guide")
        print("📘 Załadowano rozszerzenie 'guide'")
    except Exception as e:
        print(f"⚠️ Nie udało się załadować guide: {e}")

# === KOMENDY ===
# (reszta kodu z Twojej wersji — NIE zmieniaj komend PvE, PvP, sklep itd.)
# Wklej tutaj dokładnie Twoje komendy bez zmian (od !start do !ranking)

# ... [tu wklej swoje komendy z poprzedniego pliku bez zmian] ...

# === GŁÓWNE URUCHOMIENIE ===
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Błąd przy uruchamianiu bota: {e}")
