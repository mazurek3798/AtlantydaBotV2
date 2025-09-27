import discord, time
from discord.ext import commands
from discord import app_commands, ui, Interaction, Embed
from .utils import read_db, write_db, ensure_user, channel_check

class Handel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='handel', description='Przelej KA innemu użytkownikowi.')
    async def handel(self, interaction: discord.Interaction, target: discord.Member, kwota: int):
        if not channel_check(interaction.channel):
            await interaction.response.send_message('Komendy działają tylko na kanale #Atlantyda.', ephemeral=True)
            return
        if target.bot:
            await interaction.response.send_message('Nie możesz handlować z botem.', ephemeral=True); return
        if kwota <=0:
            await interaction.response.send_message('Kwota musi być > 0', ephemeral=True); return
        db = await read_db()
        uid = str(interaction.user.id); tid = str(target.id)
        ensure_user(db, uid); ensure_user(db, tid)
        sender = db['users'][uid]
        receiver = db['users'][tid]
        if sender['ka'] < kwota:
            await interaction.response.send_message('Nie masz wystarczających KA.', ephemeral=True); return
        # embed summary and confirm
        emb = Embed(title='Potwierdzenie przelewu', description=f'{interaction.user.mention} → {target.mention}\nKwota: {kwota} KA', color=0x1abc9c)
        view = ui.View(timeout=60)
        async def confirm_callback(i: Interaction):
            if i.user.id != interaction.user.id:
                await i.response.send_message('Tylko inicjator może potwierdzić.', ephemeral=True); return
            sender['ka'] -= kwota
            receiver['ka'] += kwota
            sender['spent_total'] += kwota
            receiver['earned_total'] += kwota
            sender['reputation'] += 1
            receiver['reputation'] += 1
            sender['level'] = (sender.get('earned_total',0)+sender.get('spent_total',0))//1000
            receiver['level'] = (receiver.get('earned_total',0)+receiver.get('spent_total',0))//1000
            await write_db(db)
            await i.response.edit_message(content=f'Transfer {kwota} KA wykonany do {target.mention}.', embed=None, view=None)
        async def cancel_callback(i: Interaction):
            await i.response.edit_message(content='Transakcja anulowana.', embed=None, view=None)
        btn_ok = ui.Button(label='Potwierdź', style=discord.ButtonStyle.success)
        btn_cancel = ui.Button(label='Anuluj', style=discord.ButtonStyle.danger)
        btn_ok.callback = confirm_callback
        btn_cancel.callback = cancel_callback
        view.add_item(btn_ok); view.add_item(btn_cancel)
        await interaction.response.send_message(embed=emb, view=view)

async def setup(bot):
    await bot.add_cog(Handel(bot))
