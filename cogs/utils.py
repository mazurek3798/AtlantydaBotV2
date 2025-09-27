import json, os, tempfile, asyncio
from discord.ext import commands
from discord import ui, Interaction

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.json')
LOCK = asyncio.Lock()

def atomic_write(path: str, data: str):
    dirn = os.path.dirname(path) or '.'
    fd, tmp = tempfile.mkstemp(dir=dirn)
    with os.fdopen(fd, 'w', encoding='utf-8') as w:
        w.write(data)
    os.replace(tmp, path)

async def read_db():
    async with LOCK:
        if not os.path.exists(DB_PATH):
            atomic_write(DB_PATH, '{}')
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

async def write_db(obj):
    async with LOCK:
        atomic_write(DB_PATH, json.dumps(obj, ensure_ascii=False, indent=2))

def ensure_user(db, user_id: str):
    if 'users' not in db:
        db['users'] = {}
    if user_id not in db['users']:
        db['users'][user_id] = {
            'ka': 0,
            'level': 0,
            'reputation': 0,
            'items': {},
            'daily': 0,
            'work': 0,
            'explore': 0,
            'steal_count': 0,
            'last_rp_reward': 0,
            'earned_total': 0,
            'spent_total': 0,
            'badges': [],
            'rp_xp': 0
        }

def channel_check(channel):
    return channel and channel.name == 'Atlantyda'

def level_from_ka(total_ka):
    return total_ka // 1000

class ConfirmView(ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    async def wait_for_confirm(self, interaction):
        await interaction.response.send_message('Proszę potwierdzić akcję...', view=self)
        await self.wait()
        return self.value

    @ui.button(label='Potwierdź', style=1)
    async def confirm(self, interaction: Interaction, button):
        self.value = True
        await interaction.response.edit_message(content='Potwierdzono.', view=None)
        self.stop()

    @ui.button(label='Anuluj', style=4)
    async def cancel(self, interaction: Interaction, button):
        self.value = False
        await interaction.response.edit_message(content='Anulowano.', view=None)
        self.stop()

# ==============================
# Cog z przykładową komendą
# ==============================
class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Cześć! To komenda z cogs.utils ✅")

# Funkcja setup wymagana do załadowania coga
async def setup(bot):
    await bot.add_cog(Utils(bot))
```
