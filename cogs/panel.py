import discord
import time
import random
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check


class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        embed.add_field(name="💰 Saldo", value=f"{user.get('ka', 0)} KA", inline=True)
        embed.add_field(name="📈 Poziom", value=str(user.get("level", 0)), inline=True)
        embed.add_field(name="⭐ Reputacja", value=str(user.get("reputation", 0)), inline=True)
        embed.add_field(name="🎖️ Odznaki", value=badges, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = PlayerPanelView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


class PlayerPanelView(ui.View):
    def __init__(self, owner: discord.User):
        super().__init__(timeout=120)
        self.owner = owner

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("⛔ To nie Twój panel!", ephemeral=True)
            return False
        return True

    # 🛠️ Praca (akcja bezpośrednia, cooldown 10min)
    @ui.button(label="🛠️ Praca", style=discord.ButtonStyle.green)
    async def praca(self, interaction: Interaction, button: ui.Button):
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]

        now = int(time.time())
        last = user.get("last_work", 0)
        cooldown = 10 * 60
        if now - last < cooldown:
            remaining = cooldown - (now - last)
            minutes = remaining // 60
            seconds = remaining % 60
            await interaction.response.send_message(
                f"⏳ Możesz pracować za {minutes}m {seconds}s.", ephemeral=True
            )
            return

        reward = random.randint(10, 200)
        user["ka"] = user.get("ka", 0) + reward
        user["earned_total"] = user.get("earned_total", 0) + reward
        user["last_work"] = now
        user["level"] = (user.get("earned_total", 0) + user.get("spent_total", 0)) // 1000
        await write_db(db)

        embed = discord.Embed(
            title="💼 Praca wykonana",
            description=f"{interaction.user.mention} zarobił **{reward} KA**!",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        aw
async def setup(bot):
    await bot.add_cog(Panel(bot))
