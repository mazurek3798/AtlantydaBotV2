import discord, time, random
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check

class Panel(commands.Cog):
def **init**(self, bot):
self.bot = bot

```
@app_commands.command(name="profil", description="Wyświetl swój panel gracza.")
async def profil(self, interaction: Interaction):
    if not channel_check(interaction.channel):
        await interaction.response.send_message(
            "Komendy działają tylko na kanale #Atlantyda.",
            ephemeral=True
        )
        return

    db = await read_db()
    uid = str(interaction.user.id)
    ensure_user(db, uid)
    user = db["users"][uid]

    badges = ", ".join(user.get("badges", [])[:5]) or "Brak"

    embed = discord.Embed(
        title=f"🎮 Panel gracza – {interaction.user.display_name}",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="💰 Saldo", value=f"{user['ka']} KA", inline=True)
    embed.add_field(name="📈 Poziom", value=str(user["level"]), inline=True)
    embed.add_field(name="⭐ Reputacja", value=str(user["reputation"]), inline=True)
    embed.add_field(name="🎖️ Odznaki", value=badges, inline=False)

    view = PlayerPanelView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view)
```

class PlayerPanelView(ui.View):
def **init**(self, owner: discord.User):
super().**init**(timeout=120)
self.owner = owner
self.cooldowns = {}  # cooldowny np. dla pracy

```
async def interaction_check(self, interaction: Interaction) -> bool:
    if interaction.user.id != self.owner.id:
        await interaction.response.send_message(
            "⛔ To nie Twój panel!", ephemeral=True
        )
        return False
    return True

# 🛠️ Praca
@ui.button(label="🛠️ Praca", style=discord.ButtonStyle.green)
async def praca(self, interaction: Interaction, button: ui.Button):
    db = await read_db()
    uid = str(interaction.user.id)
    ensure_user(db, uid)
    user = db["users"][uid]

    now = int(time.time())
    last = user.get("last_work", 0)
    if now - last < 600:  # 10 min
        remaining = 600 - (now - last)
        await interaction.response.send_message(
            f"⏳ Możesz pracować za {remaining//60}m {remaining%60}s.",
            ephemeral=True
        )
        return

    reward = random.randint(10, 200)
    user["ka"] += reward
    user["earned_total"] += reward
    user["last_work"] = now
    await write_db(db)

    await interaction.response.send_message(
        f"🛠️ {interaction.user.mention} pracował i zarobił **{reward} KA**!",
        ephemeral=False
    )

# 🎰 Kasyno
@ui.button(label="🎰 Kasyno", style=discord.ButtonStyle.blurple)
async def kasyno(self, interaction: Interaction, button: ui.Button):
    db = await read_db()
    uid = str(interaction.user.id)
    ensure_user(db, uid)
    user = db["users"][uid]

    stawka = 100
    if user["ka"] < stawka:
        await interaction.response.send_message(
            "💸 Nie masz wystarczająco KA, aby zagrać (100 KA wymagane).",
            ephemeral=True
        )
        return

    if random.choice([True, False]):
        user["ka"] += stawka
        user["earned_total"] += stawka
        result = f"🎉 {interaction.user.mention} WYGRAŁ w kasynie! +{stawka} KA"
    else:
        user["ka"] -= stawka
        user["spent_total"] += stawka
        user["reputation"] = max(0, user["reputation"] - 1)
        result = f"💀 {interaction.user.mention} PRZEGRAŁ w kasynie! -{stawka} KA i -1 reputacji"

    await write_db(db)
    await interaction.response.send_message(result, ephemeral=False)

# ⚔️ Pojedynek (demo vs bot)
@ui.button(label="⚔️ Pojedynek", style=discord.ButtonStyle.red)
async def pojedynek(self, interaction: Interaction, button: ui.Button):
    db = await read_db()
    uid = str(interaction.user.id)
    ensure_user(db, uid)
    user = db["users"][uid]

    stawka = 50
    if user["ka"] < stawka:
        await interaction.response.send_message(
            "⚠️ Potrzebujesz przynajmniej 50 KA, aby walczyć.",
            ephemeral=True
        )
        return

    if random.choice([True, False]):
        user["ka"] += stawka
        user["reputation"] += 2
        result = f"⚔️ {interaction.user.mention} zwyciężył w pojedynku! +{stawka} KA, +2 reputacji"
    else:
        user["ka"] -= stawka
        user["reputation"] = max(0, user["reputation"] - 1)
        result = f"💥 {interaction.user.mention} przegrał pojedynek! -{stawka} KA, -1 reputacji"

    await write_db(db)
    await interaction.response.send_message(result, ephemeral=False)

# 🛒 Sklep
@ui.button(label="🛒 Sklep", style=discord.ButtonStyle.secondary)
async def sklep(self, interaction: Interaction, button: ui.Button):
    await interaction.response.send_message(
        "🛒 Użyj `/shop`, aby zobaczyć sklep.",
        ephemeral=True
    )

# 💼 Gildia
@ui.button(label="💼 Gildia", style=discord.ButtonStyle.primary)
async def gildia(self, interaction: Interaction, button: ui.Button):
    await interaction.response.send_message(
        "🏰 Sprawdź swoje komendy gildii: `/gildia` itd.",
        ephemeral=True
    )
```

async def setup(bot):
await bot.add_cog(Panel(bot))
