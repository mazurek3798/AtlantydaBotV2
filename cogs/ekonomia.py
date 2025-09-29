import discord, random, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, channel_check, level_from_ka


class Ekonomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- RP Reward za wiadomości ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not channel_check(message.channel):
            return

        content = message.content.strip()
        if len(content) < 120:
            return

        db = await read_db()
        uid = str(message.author.id)
        ensure_user(db, uid)
        user = db["users"][uid]

        now = int(time.time())
        if now - user.get("last_rp_reward", 0) < 24 * 3600:
            return

        # nagrody
        user["ka"] += 50
        user["reputation"] += 1
        user["last_rp_reward"] = now
        user["earned_total"] += 50
        user["rp_xp"] = user.get("rp_xp", 0) + 10

        # mała szansa na artefakt
        if random.randint(1, 100) <= 8:
            user["items"]["perla_madrosci"] = user["items"].get("perla_madrosci", 0) + 1

        user["level"] = level_from_ka(user["earned_total"] + user["spent_total"])
        await write_db(db)

        try:
            await message.channel.send(
                f"{message.author.mention} otrzymuje +50 KA i +1 reputacji za wkład RP!"
            )
        except discord.Forbidden:
            pass

    # --- /saldo ---
    @app_commands.command(name="saldo", description="Pokaż swoje saldo, poziom i reputację.")
    async def saldo(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not channel_check(channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return

        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]

        badges = ", ".join(user.get("badges", [])[:5]) or "Brak"

        embed = discord.Embed(
            title=f"Saldo {interaction.user.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="💰 KA", value=str(user['ka']), inline=True)
        embed.add_field(name="⭐ Poziom", value=str(user['level']), inline=True)
        embed.add_field(name="📜 Reputacja", value=str(user['reputation']), inline=True)
        embed.add_field(name="🎖️ Odznaki", value=badges, inline=False)

        await interaction.response.send_message(embed=embed)

    # --- Autocomplete dla /ranking ---
    async def ranking_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        options = ["ka", "reputacja", "level"]
        return [
            app_commands.Choice(name=opt, value=opt)
            for opt in options
            if current.lower() in opt.lower()
        ]

    # --- /ranking ---
    @app_commands.command(name="ranking", description="Pokaż ranking top 10 (KA/reputacja/poziom).")
    @app_commands.describe(typ="Wybierz typ rankingu: ka, reputacja, poziom")
    @app_commands.autocomplete(typ=ranking_autocomplete)
    async def ranking(self, interaction: discord.Interaction, typ: str = "ka"):
        channel = interaction.channel
        if not channel_check(channel):
            await interaction.response.send_message(
                "Komendy działają tylko na kanale #Atlantyda.", ephemeral=True
            )
            return

        db = await read_db()
        users = db.get("users", {})

        typ = typ.lower()
        if typ in ("reputacja", "rep"):
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("reputation", 0), reverse=True)
            title = "🏆 Ranking Reputacji"
        elif typ in ("level", "poziom"):
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("level", 0), reverse=True)
            title = "🏆 Ranking Poziomów"
        else:
            sorted_u = sorted(users.items(), key=lambda x: x[1].get("ka", 0), reverse=True)
            title = "🏆 Ranking KA"

        embed = discord.Embed(title=title, color=discord.Color.blue())
        if not sorted_u:
            embed.description = "Brak danych."
        else:
            for i, (uid, data) in enumerate(sorted_u[:10], start=1):
                embed.add_field(
                    name=f"{i}. {self.bot.get_user(int(uid)) or 'Użytkownik'}",
                    value=(
                        f"💰 {data.get('ka',0)} KA | "
                        f"⭐ Lvl {data.get('level',0)} | "
                        f"📜 Rep {data.get('reputation',0)}"
                    ),
                    inline=False
                )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ekonomia(bot))
