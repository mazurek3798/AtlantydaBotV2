import discord, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Ekonomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='saldo', description='Pokaż swoje saldo, poziom i reputację.')
    async def saldo(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        u = db['users'][uid]
        badges = ', '.join(u.get('badges',[])[:5]) or 'Brak'
        embed = discord.Embed(title=f'💰 Saldo — {interaction.user.display_name}', color=discord.Color.gold())
        embed.add_field(name='KA', value=str(u.get('ka',0)))
        embed.add_field(name='Poziom', value=str(u.get('level',0)))
        embed.add_field(name='Reputacja', value=str(u.get('reputation',0)))
        embed.add_field(name='Odznaki', value=badges, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='ranking', description='Pokaż ranking top 10 (KA).')
    async def ranking(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True); return
        db = await read_db(); users = db.get('users',{})
        sorted_u = sorted(users.items(), key=lambda x: x[1].get('ka',0), reverse=True)[:10]
        if not sorted_u:
            await interaction.response.send_message('Brak danych.', ephemeral=True); return
        text = '\n'.join([f"{i+1}. <@{uid}> — {data.get('ka',0)} KA" for i,(uid,data) in enumerate(sorted_u)])
        await interaction.response.send_message(embed=discord.Embed(title='🏆 Ranking KA', description=text), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ekonomia(bot))
