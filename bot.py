import os, asyncio, discord
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

# Wstaw tutaj swoje GUILD_ID lub zostaw None, wtedy synchronizacja będzie globalna
GUILD_ID = 1383111630304575580  # <-- upewnij sie, ze to twoj serwer

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Zsynchronizowano {len(synced)} komend slash na serwerze {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Zsynchronizowano {len(synced)} komend slash (global)")
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
        print("Ustaw zmienna srodowiskowa DISCORD_TOKEN i sproboj ponownie.")
    else:
        asyncio.run(main())
