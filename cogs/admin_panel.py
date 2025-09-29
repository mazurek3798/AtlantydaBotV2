import discord, time
from discord.ext import commands, tasks
from discord import app_commands
from .utils import read_db, write_db, ensure_user

class AdminPanel(commands.Cog):
def **init**(self, bot):
self.bot = bot
self.weekly_task = tasks.loop(hours=24)(self.daily_checks)
self.weekly_counter = 0
self.weekly_task.start()

```
async def daily_checks(self):
    self.weekly_counter += 1
    if self.weekly_counter >= 7:
        await self.send_weekly_report()
        self.weekly_counter = 0

async def send_weekly_report(self):
    db = await read_db()
    users = db.get("users", {})
    top5 = sorted(users.items(), key=lambda x: x[1].get("ka", 0), reverse=True)[:5]
    text = "\n".join([f"{idx+1}. <@{uid}> - {data.get('ka',0)} KA" for idx,(uid,data) in enumerate(top5)])
    for guild in self.bot.guilds:
        ch = discord.utils.get(guild.text_channels, name="atlantyda")
        if ch:
            try:
                await ch.send("📊 Tygodniowy raport - top5 najbogatszych:\n" + (text or "Brak danych."))
            except Exception:
                pass

# 🔹 Dodawanie kasy
@app_commands.command(name="dodajka", description="Dodaj KA użytkownikowi (tylko administrator).")
async def dodajka(self, interaction: discord.Interaction, użytkownik: discord.Member, kwota: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
        return
    db = await read_db()
    uid = str(użytkownik.id)
    ensure_user(db, uid)
    db["users"][uid]["ka"] += kwota
    db["users"][uid]["earned_total"] += kwota
    await write_db(db)
    await interaction.response.send_message(
        f"✅ Dodano {kwota} KA dla {użytkownik.mention}. Nowe saldo: {db['users'][uid]['ka']} KA"
    )

# 🔹 Banowanie
@app_commands.command(name="banuj", description="Zbanuj użytkownika (tylko administrator).")
async def banuj(self, interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak powodu"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ Brak uprawnień do banowania.", ephemeral=True)
        return
    try:
        await użytkownik.ban(reason=powód)
        await interaction.response.send_message(f"🚫 {użytkownik.mention} został zbanowany. Powód: {powód}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Nie udało się zbanować: {e}", ephemeral=True)

# 🔹 Wyciszanie
@app_commands.command(name="wycisz", description="Wycisz użytkownika na podany czas (w minutach).")
async def wycisz(self, interaction: discord.Interaction, użytkownik: discord.Member, minuty: int, powód: str = "Brak powodu"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ Brak uprawnień do wyciszania.", ephemeral=True)
        return
    try:
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minuty)
        await użytkownik.edit(timeout=duration, reason=powód)
        await interaction.response.send_message(
            f"🔇 {użytkownik.mention} został wyciszony na {minuty} minut. Powód: {powód}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Nie udało się wyciszyć: {e}", ephemeral=True)

# 🔹 Ostrzeżenia
@app_commands.command(name="ostrzez", description="Daj ostrzeżenie użytkownikowi (tylko moderator/administrator).")
async def ostrzez(self, interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak powodu"):
    if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.moderate_members):
        await interaction.response.send_message("❌ Brak uprawnień do ostrzeżeń.", ephemeral=True)
        return
    db = await read_db()
    uid = str(użytkownik.id)
    ensure_user(db, uid)
    user = db["users"][uid]
    user["warnings"] = user.get("warnings", 0) + 1
    await write_db(db)
    await interaction.response.send_message(
        f"⚠️ {użytkownik.mention} otrzymał ostrzeżenie. (Łącznie: {user['warnings']}) Powód: {powód}"
    )

# 🔹 Zmiana gildii
@app_commands.command(name="gildia_zmien", description="Zmień nazwę gildii użytkownika (tylko administrator).")
async def gildia_zmien(self, interaction: discord.Interaction, użytkownik: discord.Member, nowa_nazwa: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
        return
    db = await read_db()
    uid = str(użytkownik.id)
    ensure_user(db, uid)
    user = db["users"][uid]
    user["guild"] = nowa_nazwa
    await write_db(db)
    await interaction.response.send_message(
        f"🏰 {użytkownik.mention} został przeniesiony do gildii **{nowa_nazwa}**"
    )
```

async def setup(bot: commands.Bot):
await bot.add_cog(AdminPanel(bot))
