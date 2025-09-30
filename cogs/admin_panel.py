import discord, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check

QUEST_DURATION = 7 * 24 * 3600  # 7 dni

class Questy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _ensure_quest(self, db, uid: str):
        ensure_user(db, uid)
        user = db["users"][uid]
        q = user.get("weekly_quest")
        now = int(time.time())
        if not q or now > q.get("until", 0):
            user["weekly_quest"] = {
                "progress": 0,
                "target": 5,
                "reward": {"ka": 300, "exp": 100},
                "done": False,
                "claimed": False,
                "until": now + QUEST_DURATION
            }

    @app_commands.command(name="tygodniowy_quest", description="Sprawdź swój quest tygodniowy.")
    async def tygodniowy_quest(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message("Komendy działają tylko na kanale #Atlantyda.", ephemeral=True)
            return

        db = await read_db()
        uid = str(interaction.user.id)
        self._ensure_quest(db, uid)
        user = db["users"][uid]
        q = user["weekly_quest"]

        status = "✅ Ukończony" if q["done"] else f"{q['progress']}/{q['target']}"

        embed = discord.Embed(
            title="🎯 Quest tygodniowy",
            description="Twoje zadanie na ten tydzień:",
            color=discord.Color.green()
        )
        embed.add_field(name="Cel", value="Napisz 5 wiadomości RP (≥120 znaków)", inline=False)
        embed.add_field(name="Postęp", value=status, inline=True)
        embed.add_field(name="Nagroda", value=f"{q['reward']['ka']} KA, {q['reward']['exp']} exp", inline=True)
        embed.add_field(name="Ważny do", value=f"<t:{q['until']}:R>", inline=False)

        await write_db(db)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim_quest", description="Odbierz nagrodę za ukończony quest tygodniowy.")
    async def claim_quest(self, interaction: discord.Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message("Komendy działają tylko na kanale #Atlantyda.", ephemeral=True)
            return

        db = await read_db()
        uid = str(interaction.user.id)
        self._ensure_quest(db, uid)
        user = db["users"][uid]
        q = user["weekly_quest"]

        if not q["done"]:
            await interaction.response.send_message("❌ Nie ukończyłeś jeszcze questa.", ephemeral=True)
            return
        if q["claimed"]:
            await interaction.response.send_message("❌ Nagroda już odebrana.", ephemeral=True)
            return

        q["claimed"] = True
        user["ka"] += q["reward"]["ka"]
        user["earned_total"] += q["reward"]["ka"]
        user["reputation"] += q["reward"]["exp"] // 50
        user["level"] = (user.get("earned_total",0) + user.get("spent_total",0)) // 1000
        await write_db(db)

        await interaction.response.send_message(
            f"🎉 Otrzymujesz {q['reward']['ka']} KA i {q['reward']['exp']} exp!"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not channel_check(message.channel):
            return
        if len(message.content.strip()) < 120:
            return

        db = await read_db()
        uid = str(message.author.id)
        self._ensure_quest(db, uid)
        user = db["users"][uid]
        q = user["weekly_quest"]

        if not q["done"]:
            q["progress"] += 1
            if q["progress"] >= q["target"]:
                q["done"] = True
        await write_db(db)

async def setup(bot):
    await bot.add_cog(Questy(bot))
