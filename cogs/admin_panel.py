import discord
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user
import time


class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ───────────────────────────────
    # KOMENDA: DODAJ KASĘ
    # ───────────────────────────────
    @app_commands.command(name="dodaj_kase", description="Dodaje KA użytkownikowi (tylko dla administratorów).")
    async def dodaj_kase(self, interaction: discord.Interaction, user: discord.Member, kwota: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tylko administrator może używać tej komendy.", ephemeral=True)
            return

        db = await read_db()
        uid = str(user.id)
        ensure_user(db, uid)

        db["users"][uid]["ka"] += kwota
        db["users"][uid]["earned_total"] += kwota
        await write_db(db)

        await interaction.response.send_message(
            f"✅ Dodano {kwota} KA dla {user.mention}. "
            f"Nowe saldo: {db['users'][uid]['ka']} KA"
        )

    # ───────────────────────────────
    # KOMENDA: ZBANUJ
    # ───────────────────────────────
    @app_commands.command(name="zbanuj", description="Banuje użytkownika (tylko dla administratorów).")
    async def zbanuj(self, interaction: discord.Interaction, user: discord.Member, powod: str = "Brak powodu"):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nie masz uprawnień do banowania.", ephemeral=True)
            return

        try:
            await user.ban(reason=powod)
            await interaction.response.send_message(f"🚫 {user.mention} został zbanowany. Powód: {powod}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Nie udało się zbanować użytkownika: {e}", ephemeral=True)

    # ───────────────────────────────
    # KOMENDA: UKARZ (WARN)
    # ───────────────────────────────
    @app_commands.command(name="ukarz", description="Daje ostrzeżenie (warn) użytkownikowi (tylko admin).")
    async def ukarz(self, interaction: discord.Interaction, user: discord.Member, powod: str = "Brak powodu"):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nie masz uprawnień do karania.", ephemeral=True)
            return

        db = await read_db()
        uid = str(user.id)
        ensure_user(db, uid)

        # dodajemy liczbę warnów
        db["users"][uid]["warns"] = db["users"][uid].get("warns", 0) + 1
        await write_db(db)

        await interaction.response.send_message(
            f"⚠️ {user.mention} otrzymał ostrzeżenie. "
            f"(Powód: {powod}) – łącznie {db['users'][uid]['warns']} ostrzeżeń."
        )

    # ───────────────────────────────
    # KOMENDA: RESET GILDII
    # ───────────────────────────────
    @app_commands.command(name="gildia_reset", description="Usuwa gildie użytkownika (tylko admin).")
    async def gildia_reset(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nie masz uprawnień do resetowania gildii.", ephemeral=True)
            return

        db = await read_db()
        uid = str(user.id)
        ensure_user(db, uid)

        if "guild" in db["users"][uid]:
            db["users"][uid].pop("guild")
            await write_db(db)
            await interaction.response.send_message(f"🏰 Gildia użytkownika {user.mention} została usunięta.")
        else:
            await interaction.response.send_message(f"ℹ️ Użytkownik {user.mention} nie miał gildii.")


# ───────────────────────────────
# SETUP
# ───────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPanel(bot))
