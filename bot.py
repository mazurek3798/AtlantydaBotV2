import os, discord, asyncio
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

initial_cogs = [
    "cogs.utils", "cogs.ekonomia", "cogs.handel", "cogs.pojedynki",
    "cogs.kradzieze", "cogs.gildie", "cogs.wydarzenia",
    "cogs.shop", "cogs.admin_panel", "cogs.praca"
]

@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Zsynchronizowano {len(synced)} komend slash")
    except Exception as e:
        print("❌ Failed to sync commands:", e)

async def load_cogs():
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            print("Loaded", cog)
        except Exception as e:
            print("Failed to load", cog, e)

async def main():
    async with bot:
        await load_cogs()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("⚠️ Ustaw zmienną środowiskową DISCORD_TOKEN i spróbuj ponownie.")
        else:
            await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
