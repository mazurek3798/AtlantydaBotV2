import random, time, discord
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_ka

COOLDOWN = 10 * 60  # 10 minut

class Praca(commands.Cog):
def **init**(self, bot):
self.bot = bot

```
@app_commands.command(name="praca", description="Idź do pracy, aby zarobić KA (co 10 minut).")
async def praca(self, interaction: discord.Interaction):
    if not channel_check(interaction.channel):
        await interaction.response.send_message(
            "Ta komenda działa tylko na kanale #Atlantyda.", 
            ephemeral=True
        )
        return

    db = await read_db()
    uid = str(interaction.user.id)
    ensure_user(db, uid)
    user = db["users"][uid]

    now = int(time.time())
    last = user.get("work", 0)

    if now - last < COOLDOWN:
        remaining = COOLDOWN - (now - last)
        minutes = remaining // 60
        seconds = remaining % 60
        await interaction.response.send_message(
            f"⏳ Musisz poczekać {minutes}m {seconds}s przed kolejną pracą.",
            ephemeral=True
        )
        return

    reward = random.randint(10, 200)
    user["ka"] += reward
    user["earned_total"] += reward
    user["work"] = now
    user["level"] = level_from_ka(user["earned_total"] + user["spent_total"])
    await write_db(db)

    await interaction.response.send_message(
        f"💼 {interaction.user.mention}, pracowałeś i zarobiłeś **{reward} KA**!"
    )
```

async def setup(bot):
await bot.add_cog(Praca(bot))
