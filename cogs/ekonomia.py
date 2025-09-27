import discord, random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_ka

# 📦 sklep (proste przedmioty)
SHOP_ITEMS = {
    "jabłko": 20,
    "mikstura": 100,
    "miecz": 500,
    "tarcza": 400,
    "perła_madrosci": 1000,
}

class Ekonomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ Nagroda RP za długą wiadomość (min. 120 znaków, raz na 24h)
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not channel_check(message.channel):
            return
        content = message.content.strip()
        if len(content) >= 120:
            db = read_db()
            uid = str(message.author.id)
            ensure_user(db, uid)
            user = db["users"][uid]
            now = int(time.time())
            if now - user.get("last_rp_reward", 0) >= 24 * 3600:
                user["ka"] += 50
                user["reputation"] += 1
                user["last_rp_reward"] = now
                user["earned_total"] += 50
                user["rp_xp"] = user.get("rp_xp", 0) + 10
                if random.randint(1, 100) <= 8:
                    user["items"]["perla_madrosci"] = user["items"].get("perla_madrosci", 0) + 1
                user["level"] = level_from_ka(user["earned_total"] + user["spent_total"])
                write_db(db)
                try:
                    await message.channel.send(
                        f"{message.author.mention} otrzymuje **+50 KA** i **+1 reputacji** za wkład RP!"
                    )
                except Exception:
                    pass

    # ✅ Komenda saldo
    @app_commands.command(name="saldo", description="Pokaż swoje saldo, poziom i reputację.")
    async def saldo(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return
        db = read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]
        badges = ", ".join(user.get("badges", [])[:5]) or "Brak"
        await interaction.response.send_message(
            f"💰 Saldo: {user['ka']} KA\n🏅 Poziom: {user['level']}\n⭐ Reputacja: {user['reputation']}\n🎖️ Odznaki: {badges}"
        )

    # ✅ Komenda ranking
    @app_commands.command(name="ranking", description="Pokaż ranking top 10 (KA/reputacja/poziom).")
    async def ranking(self, interaction: discord.Interaction, typ: str = "ka"):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return
        typ = typ.lower()
        db = read_db()
        users = db.get("users", {})
        if typ in ("reputacja", "rep"):
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("reputation", 0), reverse=True)
        elif typ in ("level", "poziom"):
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("level", 0), reverse=True)
        else:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("ka", 0), reverse=True)
        text = []
        for i, (uid, data) in enumerate(sorted_u[:10]):
            text.append(
                f"{i+1}. <@{uid}> — 💰 {data.get('ka', 0)} KA | 🏅 Lvl {data.get('level', 0)} | ⭐ Rep {data.get('reputation', 0)}"
            )
        await interaction.response.send_message("\n".join(text) or "Brak danych.")

    # ✅ Komenda daily
    @app_commands.command(name="daily", description="Odbierz nagrodę dnia (raz na 24h).")
    async def daily(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return
        db = read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]
        now = int(time.time())
        if now - user.get("daily", 0) < 24 * 3600:
            await interaction.response.send_message("⏳ Już odebrałeś nagrodę dnia. Spróbuj jutro!")
            return
        reward = random.randint(100, 200)
        user["ka"] += reward
        user["daily"] = now
        user["earned_total"] += reward
        user["level"] = level_from_ka(user["earned_total"] + user["spent_total"])
        write_db(db)
        await interaction.response.send_message(f"🎁 {interaction.user.mention} otrzymuje **{reward} KA** jako nagrodę dnia!")

    # ✅ Komenda pracuj
    @app_commands.command(name="pracuj", description="Idź do pracy i zarób KA (co godzinę).")
    async def pracuj(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return
        db = read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]
        now = int(time.time())
        if now - user.get("work", 0) < 3600:
            await interaction.response.send_message("⏳ Już pracowałeś! Spróbuj ponownie za godzinę.")
            return
        reward = random.randint(50, 150)
        user["ka"] += reward
        user["work"] = now
        user["earned_total"] += reward
        user["level"] = level_from_ka(user["earned_total"] + user["spent_total"])
        write_db(db)
        await interaction.response.send_message(f"🛠️ {interaction.user.mention} pracował i zarobił **{reward} KA**!")

    # ✅ Komenda przelej
    @app_commands.command(name="przelej", description="Przelej KA innemu użytkownikowi.")
    async def przelej(self, interaction: discord.Interaction, odbiorca: discord.Member, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return
        if odbiorca.bot:
            await interaction.response.send_message("🤖 Nie możesz przelewać KA botom!")
            return
        if kwota <= 0:
            await interaction.response.send_message("Kwota musi być większa niż 0.")
            return

        db = read_db()
        nadawca_id = str(interaction.user.id)
        odbiorca_id = str(odbiorca.id)
        ensure_user(db, nadawca_id)
        ensure_user(db, odbiorca_id)

        nadawca = db["users"][nadawca_id]
        odbiorca_data = db["users"][odbiorca_id]

        if nadawca["ka"] < kwota:
            await interaction.response.send_message("❌ Nie masz wystarczająco KA, aby zrobić przelew.")
            return

        nadawca["ka"] -= kwota
        nadawca["spent_total"] += kwota
        odbiorca_data["ka"] += kwota
        odbiorca_data["earned_total"] += kwota
        nadawca["level"] = level_from_ka(nadawca["earned_total"] + nadawca["spent_total"])
        odbiorca_data["level"] = level_from_ka(odbiorca_data["earned_total"] + odbiorca_data["spent_total"])
        write_db(db)

        await interaction.response.send_message(
            f"💸 {interaction.user.mention} przelał **{kwota} KA** dla {odbiorca.mention}!"
        )

    # ✅ Komenda sklep
    @app_commands.command(name="sklep", description="Zobacz dostępne przedmioty w sklepie.")
    async def sklep(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message("Komendy działają tylko na kanale #Atlantyda.", ephemeral=True)
            return
        items = [f"**{nazwa}** — {cena} KA" for nazwa, cena in SHOP_ITEMS.items()]
        await interact
