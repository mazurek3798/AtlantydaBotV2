import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import db_pg

load_dotenv()

TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

@bot.event
async def on_ready():
    print(f"🌊 Atlantyda RPG uruchomiona jako {bot.user}")

async def main():
    async with bot:
        await bot.load_extension("guide")
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
