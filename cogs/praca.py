```python
import discord, random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

class Praca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="praca", description="Idź do pracy, aby zarobić KA (co 10 minut).")
    async def praca(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message(
                "Komenda działa tylko na kanale #Atlantyda.", ephemeral=True
            )
            return

        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]

        now = int(time.time())
        cooldown = 10 * 60  # 10 minut
        last_work = user.get("work", 0)

        if now - last_work < cooldown:
            remaining = cooldown - (now - last_work)
            mins, secs = divmod(remaining, 60)

            embed = discord.Embed(
                title="⏳ Jeszcze odpoczywasz!",
                description=f"Możesz pracować ponownie za **{mins}m {secs}s**.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Atlantyda • Praca")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        reward = random.randint(10, 200)
        user["ka"] += reward
        user["earned_total"] += reward
        user["work"] = now

        await write_db(db)

        embed = discord.Embed(
            title="💼 Praca zakończona!",
            description=f"{interaction.user.mention} zarobił **{reward} KA** 🪙",
            color=discord.Color.green()
        )
        embed.set_footer(text="Atlantyda • Praca")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Praca(bot))
```
