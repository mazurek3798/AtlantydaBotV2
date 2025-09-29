# bot.py
import os
import asyncio
import logging
import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class AtlantydaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.initial_cogs = [
            "cogs.utils",
            "cogs.ekonomia",
            "cogs.praca",
            "cogs.kasyno",
            "cogs.pojedynki",
            "cogs.admin_panel",
            "cogs.panel",
        ]

    async def setup_hook(self):
        # load cogs
        for cog in self.initial_cogs:
            try:
                await self.load_extension(cog)
                logging.info(f"Loaded {cog}")
            except Exception as e:
                logging.exception(f"Failed to load {cog}: {e}")
        # sync commands
        try:
            await self.tree.sync()
            logging.info("Synced application commands.")
        except Exception as e:
            logging.exception(f"Failed to sync commands: {e}")

bot = AtlantydaBot()

@bot.event
async def on_ready():
    logging.info(f"✅ Zalogowano jako {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Ustaw DISCORD_TOKEN i uruchom ponownie.")
    else:
        bot.run(token)
