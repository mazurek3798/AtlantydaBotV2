import discord
from discord.ext import commands
from discord import Embed, Color
from discord.ui import View, Button

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
        if not interaction.data or "custom_id" not in interaction.data:
            return
        cid = interaction.data["custom_id"]
        if cid == "panel_profil":
            embed = Embed(title=f"Profil gracza {interaction.user.name}", description="Twoje statystyki", color=Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "panel_sklep":
            embed = Embed(title="Sklep", description="Lista przedmiotów", color=Color.gold())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "panel_gildie":
            embed = Embed(title="Gildie", description="Opcje gildii", color=Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif cid == "panel_ranking":
            embed = Embed(title="Ranking", description="Top gracze i gildie", color=Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True)

class GuideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="guide")
    async def send_guide(self, ctx):
        guide_embed = Embed(
            title="🌊 Atlantyda RPG – Przewodnik Gracza",
            description="Kliknij przyciski poniżej, aby otworzyć panele gry!",
            color=Color.teal()
        )
        view = GuideView(self.bot)
        await ctx.send(embed=guide_embed, view=view)

async def setup(bot):
    await bot.add_cog(GuideCog(bot))
    await setup_interactions(bot)
