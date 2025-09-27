import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

initial_cogs = [
    "cogs.utils", "cogs.ekonomia", "cogs.handel", "cogs.pojedynki",
    "cogs.kradzieze", "cogs.gildie", "cogs.wydarzenia", "cogs.shop", "cogs.admin_panel"
]

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend slash")
    except Exception as e:
        print("Failed to sync commands:", e)
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")

async def main():
    async with bot:
        for cog in initial_cogs:
            try:
                await bot.load_extension(cog)
                print("Loaded", cog)
            except Exception as e:
                print("Failed to load", cog, e)
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    if not os.getenv("DISCORD_TOKEN"):
        print("Ustaw zmienną środowiskową DISCORD_TOKEN i spróbuj ponownie.")
    else:
        import asyncio
        asyncio.run(main())
