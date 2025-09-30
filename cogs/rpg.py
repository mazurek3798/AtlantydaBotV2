import discord
from discord.ext import commands
import random

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- START / POSTAĆ ---
    @commands.slash_command(name="start", description="Stwórz postać")
    async def start(self, ctx, klasa: str):
        embed = discord.Embed(title="🌊 Atlantyda RPG", description=f"Twoja klasa: {klasa}", color=discord.Color.blue())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="profil", description="Pokaż profil gracza")
    async def profil(self, ctx):
        embed = discord.Embed(title="⚙️ Profil", description=f"Gracz: {ctx.author.name}", color=discord.Color.green())
        embed.add_field(name="Poziom", value="1")
        embed.add_field(name="Złoto", value="100")
        await ctx.respond(embed=embed)

    @commands.slash_command(name="ekwipunek", description="Pokaż ekwipunek")
    async def ekwipunek(self, ctx):
        embed = discord.Embed(title="🎒 Ekwipunek", description="Brak przedmiotów", color=discord.Color.purple())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="statystyki", description="Rozdziel punkty")
    async def statystyki(self, ctx):
        embed = discord.Embed(title="📊 Statystyki", description="Siła 💪: 1\nZręczność 🌀: 1\nMądrość 📖: 1\nCharyzma 👑: 1", color=discord.Color.blue())
        await ctx.respond(embed=embed)

    # --- WALKA ---
    @commands.slash_command(name="pojedynki", description="Wyzwanie PvP")
    async def pojedynki(self, ctx, gracz: discord.Member):
        dmg1 = random.randint(5,15)
        dmg2 = random.randint(5,15)
        winner = ctx.author if dmg1 >= dmg2 else gracz
        embed = discord.Embed(title="⚔️ Pojedynek", color=discord.Color.red())
        embed.add_field(name="Atak", value=f"{ctx.author.name} zadaje {dmg1}\n{gracz.name} zadaje {dmg2}")
        embed.add_field(name="Zwycięzca", value=winner.name)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="misja", description="Misja PvE")
    async def misja(self, ctx):
        loot = random.choice(["💰 Złoto", "🧪 Mikstura", "⚔️ Item", "🔮 Artefakt"])
        embed = discord.Embed(title="🗡️ Misja", description=f"Zdobyto: {loot}", color=discord.Color.red())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="trening", description="Trening postaci")
    async def trening(self, ctx):
        embed = discord.Embed(title="🏋️ Trening", description="Zyskałeś +1 do statystyki!", color=discord.Color.red())
        await ctx.respond(embed=embed)

    # --- EKONOMIA ---
    @commands.slash_command(name="sklep", description="Sklep z przedmiotami")
    async def sklep(self, ctx):
        embed = discord.Embed(title="💰 Sklep", description="1. Mikstura – 50 zł\n2. Miecz – 200 zł", color=discord.Color.gold())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="handel", description="Handel z graczem")
    async def handel(self, ctx, gracz: discord.Member):
        embed = discord.Embed(title="🤝 Handel", description=f"Rozpoczęto wymianę z {gracz.name}", color=discord.Color.gold())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="ranking", description="Ranking graczy")
    async def ranking(self, ctx):
        embed = discord.Embed(title="🏅 Ranking", description="1. GraczA – lvl 10\n2. GraczB – lvl 8", color=discord.Color.gold())
        await ctx.respond(embed=embed)

    # --- GILDIE ---
    @commands.slash_command(name="gildia", description="Zarządzanie gildią")
    async def gildia(self, ctx, akcja: str, nazwa: str=None):
        if akcja == "stwórz":
            desc = f"Gildia **{nazwa}** została stworzona!"
        elif akcja == "dołącz":
            desc = f"Dołączono do gildii {nazwa}"
        elif akcja == "opuść":
            desc = "Opuściłeś gildię"
        elif akcja == "info":
            desc = "Info o gildii"
        elif akcja == "ranking":
            desc = "TOP gildii"
        elif akcja == "wojna":
            desc = f"Wojna rozpoczęta z {nazwa}"
        else:
            desc = "Nieznana akcja"
        embed = discord.Embed(title="🏰 Gildie", description=desc, color=discord.Color.green())
        await ctx.respond(embed=embed)

    # --- ADMIN ---
    @commands.slash_command(name="admin", description="Komendy admina")
    async def admin(self, ctx, akcja: str, gracz: discord.Member=None, typ: str=None):
        if akcja == "reset":
            desc = f"Zresetowano {gracz.name}"
        elif akcja == "give":
            desc = f"Nadano {typ} graczowi {gracz.name}"
        elif akcja == "event":
            desc = "Event rozpoczęty!"
        elif akcja == "block":
            desc = f"Zablokowano {gracz.name}"
        else:
            desc = "Nieznana akcja"
        embed = discord.Embed(title="👑 Admin", description=desc, color=discord.Color.dark_gray())
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(RPG(bot))
