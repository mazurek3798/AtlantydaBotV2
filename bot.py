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

# 🔧 Wklej tutaj ID swojego serwera
GUILD_ID = 123456789012345678  

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)  # ⬅️ synchronizacja tylko na tym serwerze
        print(f"✅ Zsynchronizowano {len(synced)} komend slash na serwerze {GUILD_ID}")
    except Exception as e:
        print("❌ Nie udało się zsynchronizować komend:", e)

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
