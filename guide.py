import discord
from discord.ext import commands
from discord import Embed, Color
from discord.ui import View, Button
import db_pg, items

class GuideView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(Button(label="🧑‍💼 Profil", style=discord.ButtonStyle.primary, custom_id="panel_profil"))
        self.add_item(Button(label="🎒 Sklep / Ekwipunek", style=discord.ButtonStyle.success, custom_id="panel_sklep"))
        self.add_item(Button(label="🏰 Gildie", style=discord.ButtonStyle.danger, custom_id="panel_gildie"))
        self.add_item(Button(label="🏆 Ranking", style=discord.ButtonStyle.secondary, custom_id="panel_ranking"))

async def setup_interactions(bot: commands.Bot):
    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        if not interaction.data or 'custom_id' not in interaction.data: return
        cid = interaction.data['custom_id']; user = interaction.user
        if cid == 'panel_profil':
            p = await db_pg.get_player(user.id)
            if not p:
                await interaction.response.send_message('Nie masz postaci. Użyj !start', ephemeral=True); return
            embed = Embed(title=f"🧑‍💼 Profil — {p['name']}", color=Color.blue())
            embed.add_field(name='Klasa', value=p['class'], inline=True)
            embed.add_field(name='Poziom', value=str(p['level']), inline=True)
            embed.add_field(name='HP', value=f"{p['hp']}/{p['max_hp']}", inline=True)
            embed.add_field(name='Złoto', value=str(p['gold']), inline=True)
            inv = await db_pg.get_inventory(user.id); inv_text = ', '.join([f"{i['item_id']} x{i['qty']}" for i in inv]) or 'Brak'
            embed.add_field(name='Ekwipunek', value=inv_text, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True); return
        if cid == 'panel_sklep':
            text = '\n'.join([f"{it['id']}: {it['name']} — {it.get('price','?')}💧 (lvl {it['level']})" for it in items.ITEMS])
            embed = Embed(title='🏪 Sklep Atlantyda', description=text, color=Color.gold())
            await interaction.response.send_message(embed=embed, ephemeral=True); return
        if cid == 'panel_gildie':
            g = await db_pg.get_player_guild(user.id)
            if not g:
                await interaction.response.send_message('Nie jesteś w gildii.', ephemeral=True); return
            guild_info = await db_pg.get_guild_by_id(g['guild_id'])
            embed = Embed(title='🏰 Gildia', description=f"{guild_info['name']} — rola: {g['role']}", color=Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True); return
        if cid == 'panel_ranking':
            pool = await db_pg.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch('SELECT name, level, gold FROM players ORDER BY level DESC, gold DESC LIMIT 10')
            txt = '\n'.join([f"{r['name']} — lvl {r['level']} ({r['gold']}💧)" for r in rows]) or 'Brak graczy'
            embed = Embed(title='🏆 Ranking TOP 10', description=txt, color=Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True); return

class GuideCog(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.command(name='guide')
    async def send_guide(self, ctx):
        guide_embed = Embed(title='🌊 Atlantyda RPG — Przewodnik Gracza', description='Kliknij przyciski, aby otworzyć panele!', color=Color.teal())
        view = GuideView(self.bot)
        await ctx.send(embed=guide_embed, view=view)

async def setup(bot):
    await bot.add_cog(GuideCog(bot))
    await setup_interactions(bot)
