import discord
from discord.ext import commands
import aiosqlite

def xp_required(level: int) -> int:
    """Oblicza ile XP potrzeba na kolejny poziom."""
    return 100 * level

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_player(self, user_id: int):
        """Tworzy rekord gracza, jeśli nie istnieje."""
        async with aiosqlite.connect("database.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    gold INTEGER DEFAULT 100,
                    strength INTEGER DEFAULT 5,
                    agility INTEGER DEFAULT 5,
                    wisdom INTEGER DEFAULT 5,
                    charisma INTEGER DEFAULT 5
                )
            """)
            await db.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def add_xp(self, user_id: int, amount: int):
        """Dodaje XP i sprawdza awans poziomu."""
        await self.ensure_player(user_id)
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT xp, level FROM players WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()

            xp, level = row
            xp += amount
            leveled_up = False

            # sprawdzanie awansu
            while xp >= xp_required(level):
                xp -= xp_required(level)
                level += 1
                leveled_up = True

                # wzrost statystyk przy level up
                await db.execute("""
                    UPDATE players
                    SET strength = strength + 2,
                        agility = agility + 2,
                        wisdom = wisdom + 2,
                        charisma = charisma + 2
                    WHERE user_id = ?
                """, (user_id,))

            await db.execute("UPDATE players SET xp = ?, level = ? WHERE user_id = ?", (xp, level, user_id))
            await db.commit()
            return leveled_up, level, xp

    @commands.hybrid_command(name="start", description="Rozpocznij przygodę w Atlantydzie!")
    async def start(self, ctx: commands.Context):
        await self.ensure_player(ctx.author.id)
        embed = discord.Embed(
            title="🌊 Witaj w Atlantydzie!",
            description="Twoja przygoda się zaczyna! Zdobywaj XP, złoto i awansuj na wyższe poziomy.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Użyj /profil aby zobaczyć swoją postać.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="profil", description="Zobacz swój profil RPG.")
    async def profil(self, ctx: commands.Context):
        await self.ensure_player(ctx.author.id)
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT level, xp, gold, strength, agility, wisdom, charisma FROM players WHERE user_id = ?", (ctx.author.id,)) as cursor:
                data = await cursor.fetchone()

        level, xp, gold, str_, agi, wis, cha = data
        embed = discord.Embed(title=f"👤 Profil gracza {ctx.author.display_name}", color=discord.Color.teal())
        embed.add_field(name="🏅 Poziom", value=level)
        embed.add_field(name="✨ Doświadczenie", value=f"{xp}/{xp_required(level)}")
        embed.add_field(name="💰 Złoto", value=gold)
        embed.add_field(name="💪 Siła", value=str_)
        embed.add_field(name="🌀 Zręczność", value=agi)
        embed.add_field(name="📖 Mądrość", value=wis)
        embed.add_field(name="👑 Charyzma", value=cha)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="trening", description="Trenuj, aby zdobyć doświadczenie (koszt 10 złota).")
    async def trening(self, ctx: commands.Context):
        await self.ensure_player(ctx.author.id)
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT gold FROM players WHERE user_id = ?", (ctx.author.id,)) as cursor:
                gold = (await cursor.fetchone())[0]

            if gold < 10:
                embed = discord.Embed(
                    title="❌ Za mało złota!",
                    description="Trening kosztuje 💰 10 złota.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            # potrącamy złoto
            await db.execute("UPDATE players SET gold = gold - 10 WHERE user_id = ?", (ctx.author.id,))
            await db.commit()

        # dodajemy XP
        leveled_up, new_level, xp = await self.add_xp(ctx.author.id, 15)

        embed = discord.Embed(
            title="🏋️ Trening zakończony!",
            description=f"Zdobyłeś **15 XP**! (📈 {xp} XP)",
            color=discord.Color.gold()
        )

        if leveled_up:
            embed.add_field(name="🎉 Awans!", value=f"Nowy poziom: **{new_level}**", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RPG(bot))
