import discord, time
from discord.ext import commands
from discord import app_commands
from .utils import read_db, write_db, ensure_user, add_admin_log, channel_check

class AdminPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='dodajka', description='Dodaj KA użytkownikowi (admin).')
    async def dodajka(self, interaction: app_commands.Context, member: discord.Member, kwota: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('Brak uprawnień.', ephemeral=True); return
        db = await read_db(); uid = str(member.id); ensure_user(db, uid)
        db['users'][uid]['ka'] += kwota; db['users'][uid]['earned_total'] += kwota
        add_admin_log(db, interaction.user.id, 'dodajka', member.id, str(kwota))
        await write_db(db); await interaction.response.send_message(f'✅ Dodano {kwota} KA do {member.mention}')

    @app_commands.command(name='banuj', description='Zbanuj użytkownika (admin).')
    async def banuj(self, interaction: app_commands.Context, member: discord.Member, powod: str = 'Brak powodu'):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message('Brak uprawnień.', ephemeral=True); return
        try:
            await member.ban(reason=powod)
            db = await read_db(); add_admin_log(db, interaction.user.id, 'banuj', member.id, powod); await write_db(db)
            await interaction.response.send_message(f'🚫 {member.mention} zbanowany. Powód: {powod}')
        except Exception as e:
            await interaction.response.send_message(f'Nie udało się zbanować: {e}', ephemeral=True)

    @app_commands.command(name='ostrzez', description='Dodaj ostrzeżenie (admin).')
    async def ostrzez(self, interaction: app_commands.Context, member: discord.Member, powod: str = 'Brak powodu'):
        if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.moderate_members):
            await interaction.response.send_message('Brak uprawnień.', ephemeral=True); return
        db = await read_db(); uid = str(member.id); ensure_user(db, uid)
        db['users'][uid]['warnings'] = db['users'][uid].get('warnings',0) + 1
        add_admin_log(db, interaction.user.id, 'ostrzez', member.id, powod)
        await write_db(db); await interaction.response.send_message(f'⚠️ {member.mention} otrzymał ostrzeżenie. Powód: {powod}')

async def setup(bot):
    await bot.add_cog(AdminPanel(bot))
