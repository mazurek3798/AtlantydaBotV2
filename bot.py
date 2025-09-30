import discord
from discord.ext import commands
import asyncio
import os

# --- MIGRACJA ---
try:
    from migrate_v2_to_v3 import migrate
    print("Sprawdzam migracje bazy...")
    try:
        migrate()
    except Exception as e:
        print("Błąd migracji (możesz mieć nową bazę):", e)
except Exception:
    pass
# ----------------

import db

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")

async def main():
    async with bot:
        await db.init_db()
        await bot.load_extension("cogs.rpg")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
