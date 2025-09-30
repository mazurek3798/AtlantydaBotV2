import os
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
import asyncio

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

TOKEN = os.getenv("DISCORD_TOKEN") or ""
OWNER_ID = int(os.getenv("OWNER_ID") or 0)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents, description="Atlantyda RPG")

async def load_all_cogs():
    for p in (Path(__file__).parent / "cogs").glob("*.py"):
        name = f"cogs.{p.stem}"
        try:
            await bot.load_extension(name)
            print("Loaded", name)
        except Exception as e:
            print("Failed to load", name, e)

@bot.event
async def on_ready():
    print("Bot ready:", bot.user)
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Sync failed:", e)

    await load_all_cogs()

if __name__ == "__main__":
    if not TOKEN:
        print("Set DISCORD_TOKEN in .env (see .env.example)")
    else:
        bot.run(TOKEN)
