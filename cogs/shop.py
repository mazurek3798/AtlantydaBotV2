import discord, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='sklep', description='Pokaż dostępne przedmioty.')
    async def sklep(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        shop = db.get('shop',{})
        text = '\n'.join([f"{k}: {v['name']} - {v['price']} KA - {v['desc']}" for k,v in shop.items()])
        await interaction.response.send_message('Sklep:\n'+text)

    @app_commands.command(name='kup', description='Kup przedmiot ze sklepu.')
    async def kup(self, interaction: discord.Interaction, item_key: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        shop = db.get('shop',{})
        if item_key not in shop:
            await interaction.response.send_message('Brak takiego przedmiotu.', ephemeral=True); return
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db['users'][uid]
        item = shop[item_key]
        if user['ka'] < item['price']:
            await interaction.response.send_message('Nie masz wystarczająco KA.', ephemeral=True); return
        user['ka'] -= item['price']
        user['items'][item_key] = user['items'].get(item_key,0) + 1
        user['spent_total'] += item['price']
        user['level'] = (user.get('earned_total',0)+user.get('spent_total',0))//1000
        await write_db(db)
        await interaction.response.send_message(f'Zakupiłeś {item["name"]}.')

    @app_commands.command(name='uzyj', description='Użyj przedmiotu (jeśli jednorazowy).')
    async def uzyj(self, interaction: discord.Interaction, item_key: str):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id); ensure_user(db, uid)
        user = db['users'][uid]
        if item_key not in user.get('items',{}):
            await interaction.response.send_message('Nie posiadasz tego przedmiotu.', ephemeral=True); return
        # define consumables
        if item_key == 'muszla':
            # grants immediate daily if not used today
            now = int(time.time())
            if now - user.get('daily',0) < 24*3600:
                await interaction.response.send_message('Już korzystałeś z codziennego w ciągu 24h.', ephemeral=True); return
            user['daily'] = now
            gain = 100
            user['ka'] += gain
            user['earned_total'] += gain
            await interaction.response.send_message(f'Muszla Syreny użyta — otrzymujesz {gain} KA.')
        elif item_key == 'eliksir':
            await interaction.response.send_message('Eliksir gotowy do użycia przy następnym /kradnij (automatycznie zużyty).')
        else:
            await interaction.response.send_message('Ten przedmiot nie jest jednorazowy lub jego użycie jest pasywne.')
        # consume one
        user['items'][item_key] -= 1
        if user['items'][item_key] <=0:
            del user['items'][item_key]
        await write_db(db)

async def setup(bot):
    await bot.add_cog(Shop(bot))
