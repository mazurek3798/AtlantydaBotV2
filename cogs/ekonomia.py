import discord
from discord import app_commands
from discord.ext import commands
import random, time
from .utils import read_db, write_db, ensure_user

GUILD_ID = 1383111630304575580  # ID Twojego serwera

class Ekonomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Odbierz swoją dzienną nagrodę")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def daily(self, interaction: discord.Interaction):
        db = await read_db()
        user_id = str(interaction.user.id)
        ensure_user(db, user_id)

        teraz = time.time()
        ostatni_daily = db["users"][user_id]["daily"]

        if teraz - ostatni_daily < 24 * 3600:
            pozostalo = int((24 * 3600 - (teraz - ostatni_daily)) // 3600)
            await interaction.response.send_message(
                f"❌ Już odebrałeś dzisiejszą nagrodę! Spróbuj ponownie za {pozostalo} godzin.",
                ephemeral=True
            )
            return

        nagroda = random.randint(100, 300)
        db["users"][user_id]["ka"] += nagroda
        db["users"][user_id]["daily"] = teraz
        await write_db(db)

        await interaction.response.send_message(f"✅ Odebrałeś dzienną nagrodę: **{nagroda}💰**")

    @app_commands.command(name="work", description="Idź do pracy i zarób monety")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def work(self, interaction: discord.Interaction):
        db = await read_db()
        user_id = str(interaction.user.id)
        ensure_user(db, user_id)

        teraz = time.time()
        ostatnia_praca = db["users"][user_id]["work"]

        if teraz - ostatnia_praca < 3600:  # cooldown 1h
            pozostalo = int((3600 - (teraz - ostatnia_praca)) // 60)
            await interaction.response.send_message(
                f"❌ Już dziś pracowałeś! Spróbuj ponownie za {pozostalo} minut.",
                ephemeral=True
            )
            return

        zarobek = random.randint(50, 150)
        prace = ["programistą", "kelnerem", "rolnikiem", "górnikiem", "budowlańcem"]
        praca = random.choice(prace)

        db["users"][user_id]["ka"] += zarobek
        db["users"][user_id]["work"] = teraz
        await write_db(db)

        await interaction.response.send_message(
            f"💼 Pracowałeś jako **{praca}** i zarobiłeś **{zarobek}💰**!"
        )

    @app_commands.command(name="saldo", description="Sprawdź ile masz monet")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def saldo(self, interaction: discord.Interaction):
        db = await read_db()
        user_id = str(interaction.user.id)
        ensure_user(db, user_id)

        kasa = db["users"][user_id]["ka"]
        reputacja = db["users"][user_id]["reputation"]
        level = db["users"][user_id]["level"]

        await interaction.response.send_message(
            f"💰 Masz **{kasa}** monet.\n⭐ Poziom: {level}\n📈 Reputacja: {reputacja}"
        )

    @app_commands.command(name="daj", description="Przekaż monety innej osobie")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def daj(self, interaction: discord.Interaction, osoba: discord.Member, kwota: int):
        if kwota <= 0:
            await interaction.response.send_message("❌ Kwota musi być większa od zera.", ephemeral=True)
            return

        db = await read_db()
        nadawca_id = str(interaction.user.id)
        odbiorca_id = str(osoba.id)

        ensure_user(db, nadawca_id)
        ensure_user(db, odbiorca_id)

        if db["users"][nadawca_id]["ka"] < kwota:
            await interaction.response.send_message("❌ Nie masz wystarczająco monet.", ephemeral=True)
            return

        db["users"][nadawca_id]["ka"] -= kwota
        db["users"][odbiorca_id]["ka"] += kwota
        await write_db(db)

        await interaction.response.send_message(
            f"✅ Przekazałeś **{kwota}💰** użytkownikowi {osoba.mention}."
        )

async def setup(bot):
    await bot.add_cog(Ekonomia(bot))
