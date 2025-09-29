import os, discord, asyncio
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

initial_cogs = [
    'cogs.utils', 'cogs.ekonomia', 'cogs.handel', 'cogs.pojedynki',
    'cogs.kradzieze', 'cogs.gildie', 'cogs.wydarzenia', 'cogs.shop', 'cogs.admin_panel','cogs.praca'
]

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            print('Loaded', cog)
        except Exception as e:
            print('Failed to load', cog, e)
    try:
        await bot.tree.sync()
    except Exception as e:
        print('Failed to sync commands', e)
await bot.load_extension("cogs.praca")

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('Ustaw zmienną środowiskową DISCORD_TOKEN i spróbuj ponownie.')
    else:
        bot.run(token)

