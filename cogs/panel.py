# cogs/panel.py
import discord
import time
import random
from discord.ext import commands
from discord import app_commands, ui, Interaction
from .utils import read_db, write_db, ensure_user, channel_check

# Helper: znajdź cog po liście możliwych nazw (case-insensitive)
def find_cog(bot, *names):
    names = [n.lower() for n in names]
    for k, cog in bot.cogs.items():
        if k.lower() in names:
            return cog
    return None

class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="panel", description="Otwiera graficzny panel gracza / admina.")
    async def panel(self, interaction: Interaction):
        if not channel_check(interaction.channel):
            await interaction.response.send_message("Komendy działają tylko na kanale #Atlantyda.", ephemeral=True)
            return

        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]

        badges = ", ".join(user.get("badges", [])[:5]) or "Brak"

        embed = discord.Embed(
            title=f"🎮 Panel – {interaction.user.display_name}",
            description="Kliknij przycisk, żeby wykonać akcję.",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{user.get('ka',0)} KA", inline=True)
        embed.add_field(name="📈 Poziom", value=str(user.get("level",0)), inline=True)
        embed.add_field(name="⭐ Reputacja", value=str(user.get("reputation",0)), inline=True)
        embed.add_field(name="🎖️ Odznaki", value=badges, inline=False)

        view = FullPanelView(self.bot, interaction.user)
        # jeśli admin -> dopisz admin controls do tego samego widoku
        if interaction.user.guild_permissions.administrator:
            view.add_admin_buttons = True
            view.build_admin_buttons()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class FullPanelView(ui.View):
    """
    Widok przycisków dla panelu. Ma logikę, która wywołuje istniejące cogi,
    jeśli są zainstalowane; w przeciwnym razie bezpiecznie odpowiada.
    """
    def __init__(self, bot: commands.Bot, owner: discord.User):
        super().__init__(timeout=300)
        self.bot = bot
        self.owner = owner
        self.add_admin_buttons = False
        # zbuduj podstawowe przyciski:
        # (dodawanie admin buttons wywołuje build_admin_buttons())
        self._build_player_buttons()

    def _build_player_buttons(self):
        # Praca
        self.add_item(ui.Button(label="🛠️ Praca", style=discord.ButtonStyle.green, custom_id="panel_praca"))
        # Saldo
        self.add_item(ui.Button(label="💰 Saldo", style=discord.ButtonStyle.primary, custom_id="panel_saldo"))
        # Ranking
        self.add_item(ui.Button(label="🏆 Ranking", style=discord.ButtonStyle.secondary, custom_id="panel_ranking"))
        # Kasyno
        self.add_item(ui.Button(label="🎰 Kasyno", style=discord.ButtonStyle.danger, custom_id="panel_kasyno"))
        # Pojedynek
        self.add_item(ui.Button(label="⚔️ Pojedynek", style=discord.ButtonStyle.blurple, custom_id="panel_pojedynek"))
        # Handel / Sklep
        self.add_item(ui.Button(label="🛒 Sklep", style=discord.ButtonStyle.gray, custom_id="panel_shop"))
        # Gildie
        self.add_item(ui.Button(label="🏰 Gildia", style=discord.ButtonStyle.primary, custom_id="panel_gildie"))

    def build_admin_buttons(self):
        # admin buttons appended at end
        # Dodaj przycisk 'Panel Admina' (otwiera modal z opcjami)
        self.add_item(ui.Button(label="🔧 Panel Admina", style=discord.ButtonStyle.blurple, custom_id="panel_admin"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # tylko właściciel panela i admin (dla admin buttons) mogą użyć - ale admin może użyć także
        if interaction.user.id == self.owner.id:
            return True
        # jeśli admin button i user admin -> allow
        if interaction.data and interaction.data.get("custom_id","").startswith("admin_"):
            return interaction.user.guild_permissions.administrator
        await interaction.response.send_message("⛔ To nie Twój panel!", ephemeral=True)
        return False

    # global handler: obsługa kliknięć przycisków używając custom_id
    @ui.button(label=" ", style=discord.ButtonStyle.grey, custom_id="__dummy__", disabled=True)
    async def _dummy(self, interaction: Interaction, button: ui.Button):
        # dummy to zapobiega pustemu view bez elementów, nie używamy go
        pass

    @commands.Cog.listener()
    async def on_error(self, *a, **k):
        pass

    # Override interaction handler (obsłużymy custom_id)
    async def on_timeout(self):
        try:
            # po timeout usuń przyciski (próba edycji)
            for child in self.children:
                child.disabled = True
        except Exception:
            pass

    async def _reply_not_owner(self, interaction: Interaction):
        await interaction.response.send_message("⛔ To nie Twój panel!", ephemeral=True)

    # --- obsługa przycisków ---
    @ui.button(label=" ", style=discord.ButtonStyle.gray, custom_id="__placeholder__", disabled=True)
    async def placeholder(self, interaction: Interaction, button: ui.Button):
        # button placeholder żeby dekoratory dobrze działały - nie wykonywany
        pass

    # Użyj raw_interaction handlera: w discord.py nie ma "on_button_click" globalnie w View,
    # ale callbacky są powiązane z Button.item.callback. Niestety dynamiczne callbacky z custom_id
    # nie są bezpośrednio dostępne, więc rejestrujemy przyciski z konkretnymi callbackami poniżej.
    # Dlatego poniżej dodaję callbacki dla znanych custom_id.

    # Praca
    @ui.button(label="🛠️ PRACA (placeholder)", style=discord.ButtonStyle.green, custom_id="panel_praca_cb", disabled=True)
    async def _praca_cb_placeholder(self, interaction: Interaction, button: ui.Button):
        pass

    # Ale zamiast dekoratorów powyżej, spowodujemy, że w czasie init nie mają przypisanych callbacków.
    # Aby uniknąć komplikacji z dekoratorami i dynamicznością, poniżej znajduje się metoda "start" do rebind.

    async def interaction_check(self, interaction: Interaction) -> bool:
        # allow only owner or admins for admin buttons
        if interaction.user.id == self.owner.id:
            return True
        if interaction.data and isinstance(interaction.data, dict):
            cid = interaction.data.get("custom_id","")
            if cid.startswith("admin_") and interaction.user.guild_permissions.administrator:
                return True
        await interaction.response.send_message("⛔ To nie Twój panel!", ephemeral=True)
        return False

    # Because dynamic callback binding via custom_id is cumbersome with decorators, we provide per-button callbacks here:
    async def on_button_click(self, interaction: Interaction):
        # fallback if needed
        await interaction.response.send_message("Nieobsługiwany przycisk.", ephemeral=True)

    # Instead of relying on decorators for dynamic buttons, we'll attach callbacks in runtime.
    async def _run_action_by_id(self, interaction: Interaction, custom_id: str):
        # dispatch based on custom_id
        if custom_id == "panel_praca":
            await self._do_praca(interaction)
        elif custom_id == "panel_saldo":
            await self._do_saldo(interaction)
        elif custom_id == "panel_ranking":
            await self._do_ranking(interaction)
        elif custom_id == "panel_kasyno":
            await self._do_kasyno(interaction)
        elif custom_id == "panel_pojedynek":
            await self._do_pojedynek_modal(interaction)
        elif custom_id == "panel_shop":
            await interaction.response.send_message("🛒 Użyj `/shop` aby otworzyć sklep.", ephemeral=True)
        elif custom_id == "panel_gildie":
            await interaction.response.send_message("🏰 Użyj komend gildii (np. `/gildia`).", ephemeral=True)
        elif custom_id == "panel_admin":
            await self._open_admin_modal(interaction)
        else:
            await interaction.response.send_message("Nieznany przycisk.", ephemeral=True)

    # Concrete implementations (które wywołują inne cogi, jeśli są)
    async def _do_praca(self, interaction: Interaction):
        # Spróbuj znaleźć cog 'Praca' i wywołać jego metodę praca(interaction)
        cog = find_cog(self.bot, "Praca", "praca")
        if cog and hasattr(cog, "praca"):
            try:
                # bound method will take interaction
                await getattr(cog, "praca")(interaction)
                return
            except Exception:
                # fallback do lokalnej prostej pracy
                pass

        # fallback: prosty praca logic
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]
        now = int(time.time())
        if now - user.get("last_work", 0) < 10 * 60:
            remaining = 10 * 60 - (now - user["last_work"])
            await interaction.response.send_message(f"⏳ Możesz pracować za {remaining//60}m {remaining%60}s.", ephemeral=True)
            return
        reward = random.randint(10, 200)
        user["ka"] = user.get("ka", 0) + reward
        user["earned_total"] = user.get("earned_total", 0) + reward
        user["last_work"] = now
        await write_db(db)
        await interaction.response.send_message(f"🛠️ Pracowałeś i zarobiłeś **{reward} KA**!", ephemeral=True)

    async def _do_saldo(self, interaction: Interaction):
        cog = find_cog(self.bot, "Ekonomia", "ekonomia")
        if cog and hasattr(cog, "saldo"):
            try:
                await getattr(cog, "saldo")(cog, interaction) if False else await getattr(cog, "saldo")(interaction)
                # Some cog methods are app_command bound methods (require self). If above fails, try calling as bound.
            except Exception:
                # attempt calling bound method
                try:
                    bound = getattr(cog, "saldo")
                    await bound(interaction)
                    return
                except Exception:
                    pass
        # fallback: show data directly
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        u = db["users"][uid]
        badges = ", ".join(u.get("badges", [])[:5]) or "Brak"
        await interaction.response.send_message(f"💰 Saldo: {u.get('ka',0)} KA\nPoziom: {u.get('level',0)}\nReputacja: {u.get('reputation',0)}\nOdznaki: {badges}", ephemeral=True)

    async def _do_ranking(self, interaction: Interaction):
        cog = find_cog(self.bot, "Ekonomia", "ekonomia")
        if cog and hasattr(cog, "ranking"):
            try:
                await getattr(cog, "ranking")(interaction)  # expects (interaction, typ='ka') usually
                return
            except Exception:
                pass
        db = await read_db()
        users = db.get("users", {})
        sorted_u = sorted(users.items(), key=lambda x: x[1].get("ka", 0), reverse=True)
        text = []
        for idx, (uid, data) in enumerate(sorted_u[:10]):
            text.append(f"{idx+1}. <@{uid}> - {data.get('ka',0)} KA / Lvl {data.get('level',0)} / Rep {data.get('reputation',0)}")
        await interaction.response.send_message("🏆 Top 10:\n" + ("\n".join(text) if text else "Brak danych."), ephemeral=True)

    async def _do_kasyno(self, interaction: Interaction):
        # If there's a Kasyno cog, try calling it
        cog = find_cog(self.bot, "Kasyno", "kasyno")
        if cog and hasattr(cog, "kasyno"):
            try:
                await getattr(cog, "kasyno")(interaction)  # some implementations may differ
                return
            except Exception:
                pass
        # fallback simple kasyno (50% win x2, lose = -bet and -1 rep)
        db = await read_db()
        uid = str(interaction.user.id)
        ensure_user(db, uid)
        user = db["users"][uid]
        bet = 100
        if user.get("ka", 0) < bet:
            await interaction.response.send_message(f"💸 Potrzebujesz przynajmniej {bet} KA aby zagrać.", ephemeral=True)
            return
        win = random.choice([True, False])
        if win:
            user["ka"] += bet
            user["earned_total"] = user.get("earned_total", 0) + bet
            reply = f"🎉 WYGRAŁEŚ! Otrzymujesz +{bet} KA."
        else:
            user["ka"] = max(0, user.get("ka", 0) - bet)
            user["spent_total"] = user.get("spent_total", 0) + bet
            user["reputation"] = max(0, user.get("reputation", 0) - 1)
            reply = f"💀 PRZEGRAŁEŚ! Tracisz {bet} KA i -1 reputacji."
        user["level"] = (user.get("earned_total",0) + user.get("spent_total",0)) // 1000
        await write_db(db)
        await interaction.response.send_message(reply, ephemeral=True)

    async def _do_pojedynek_modal(self, interaction: Interaction):
        # Otwórz modal, aby wpisać ID/mention oraz stawkę, a po zatwierdzeniu spróbuj wywołać cog 'Pojedynki'
        modal = DuelInputModal(self.bot)
        await interaction.response.send_modal(modal)

    # Admin modal opener
    async def _open_admin_modal(self, interaction: Interaction):
        # check admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tylko administrator może korzystać z panelu admina.", ephemeral=True)
            return
        modal = AdminActionModal(self.bot)
        await interaction.response.send_modal(modal)

    # We need to intercept component interactions: dispatch by custom_id.
    async def interaction_check(self, interaction: Interaction) -> bool:
        # allow owner or admins for admin buttons
        if interaction.user.id == self.owner.id:
            return True
        # allow admin to use admin modal
        cid = interaction.data.get("custom_id", "") if isinstance(interaction.data, dict) else ""
        if cid == "panel_admin" and interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("⛔ To nie Twój panel!", ephemeral=True)
        return False

    # Since we used Buttons with custom_id in _build_player_buttons, Discord will call the callback
    # associated with those Button instances only if they had callback functions bound.
    # As we built buttons without specific callbacks, we handle interactions at the view level by overriding 'interaction_check'
    # and using on_error/on_timeout. Unfortunately discord.py currently does not expose a single "on_button" on View.
    # To catch the button presses, we rely on the fact that Button callback is set to the view's `on_item_interaction` via the library.
    # Simpler: register an interaction handler via a Cog listener for 'on_interaction' (below) to route to this view.

# Modal for duel input
class DuelInputModal(ui.Modal, title="Wyzwanie — wpisz target i stawkę"):
    target = ui.TextInput(label="Target (ID lub @mention)", placeholder="np. 123456789012345678 lub @User", required=True)
    stawka = ui.TextInput(label="Stawka (liczba)", placeholder="np. 50", required=True, max_length=10)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        raw_target = self.target.value.strip()
        raw_stawka = self.stawka.value.strip()
        try:
            stawka = int(raw_stawka)
            if raw_target.startswith("<@") and raw_target.endswith(">"):
                raw_target = raw_target.replace("<@", "").replace(">", "").replace("!", "")
            target_id = int(raw_target)
        except Exception:
            await interaction.response.send_message("❌ Niepoprawny target lub stawka.", ephemeral=True)
            return

        # Try to call Pojedynki cog's command if present
        cog = find_cog(self.bot, "Pojedynki", "pojedynki")
        if cog and hasattr(cog, "pojedynek"):
            # build a fake call: call bound method on cog
            target_member = interaction.guild.get_member(target_id) if interaction.guild else None
            try:
                # call cog.pojedynek(interaction, target_member, stawka)
                await getattr(cog, "pojedynek")(interaction, target_member, stawka)
                return
            except Exception:
                # fallback to internal duel flow below
                pass

        # fallback: simple duel resolved immediately between interactor and target
        db = await read_db()
        uid = str(interaction.user.id)
        tid = str(target_id)
        ensure_user(db, uid)
        ensure_user(db, tid)
        a = db["users"][uid]
        b = db["users"][tid]

        if stawka <= 0:
            await interaction.response.send_message("❌ Stawka musi być > 0", ephemeral=True); return
        if stawka > a.get("ka",0)*0.5 or stawka > b.get("ka",0)*0.5:
            await interaction.response.send_message("❌ Stawka nie może przekraczać 50% salda któregoś z graczy.", ephemeral=True); return
        # compute chance
        chance = 50 + (a.get("level",0)-b.get("level",0))*5
        roll = random.randint(1,100)
        if roll <= chance:
            a["ka"] += stawka
            b["ka"] -= stawka
            a["earned_total"] = a.get("earned_total",0)+stawka
            b["spent_total"] = b.get("spent_total",0)+stawka
            a["reputation"] = a.get("reputation",0)+2
            b["reputation"] = max(0, b.get("reputation",0)-1)
            desc = f"🏆 <@{interaction.user.id}> wygrał i zdobywa {stawka} KA!"
        else:
            b["ka"] += stawka
            a["ka"] -= stawka
            b["earned_total"] = b.get("earned_total",0)+stawka
            a["spent_total"] = a.get("spent_total",0)+stawka
            b["reputation"] = b.get("reputation",0)+2
            a["reputation"] = max(0, a.get("reputation",0)-1)
            desc = f"🏆 <@{target_id}> wygrał i zdobywa {stawka} KA!"
        a["ka"] = max(0, a.get("ka",0)); b["ka"] = max(0, b.get("ka",0))
        a["level"] = (a.get("earned_total",0)+a.get("spent_total",0))//1000
        b["level"] = (b.get("earned_total",0)+b.get("spent_total",0))//1000
        await write_db(db)
        await interaction.response.send_message(desc)

# Admin actions modal
class AdminActionModal(ui.Modal, title="Panel admina — akcja"):
    action = ui.TextInput(label="Akcja (dodajka/banuj/ostrzeż/gildia_zmien)", placeholder="np. dodajka", required=True)
    target = ui.TextInput(label="Target (ID lub @mention)", placeholder="np. 123456789012345678", required=False)
    amount = ui.TextInput(label="Kwota (jeśli dotyczy)", placeholder="np. 1000", required=False, max_length=20)
    reason = ui.TextInput(label="Powód (opcjonalnie)", placeholder="Powód", required=False, max_length=200)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
            return
        act = self.action.value.strip().lower()
        raw_target = self.target.value.strip()
        amount = self.amount.value.strip()
        reason = self.reason.value.strip() or "Brak powodu"

        # parse target id
        target_id = None
        if raw_target:
            try:
                if raw_target.startswith("<@") and raw_target.endswith(">"):
                    raw_target = raw_target.replace("<@", "").replace(">", "").replace("!", "")
                target_id = int(raw_target)
            except Exception:
                await interaction.response.send_message("❌ Niepoprawny target.", ephemeral=True)
                return

        db = await read_db()

        # Try to call AdminPanel cog if exists
        admin_cog = find_cog(self.bot, "AdminPanel", "admin_panel", "Admin")
        if admin_cog:
            # attempt mapping: dodajka -> admin_cog.dodajka, banuj -> admin_cog.banuj, ostrzez/ukarz -> admin_cog.ostrzez, gildia_zmien -> admin_cog.gildia_zmien
            try:
                if act.startswith("dodaj"):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    amt = int(amount) if amount else 0
                    await getattr(admin_cog, "dodajka")(interaction, member, amt)
                    return
                if act in ("banuj", "ban"):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await getattr(admin_cog, "banuj")(interaction, member, reason)
                    return
                if act in ("ostrzez", "ukarz", "warn"):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await getattr(admin_cog, "ostrzez")(interaction, member, reason)
                    return
                if act in ("gildia_zmien", "gildia"):
                    member = interaction.guild.get_member(target_id) if target_id else None
                    await getattr(admin_cog, "gildia_zmien")(interaction, member, amount or "")
                    return
            except Exception:
                # fall through to built-in handling
                pass

        # fallback internal admin actions (modify DB directly)
        if act.startswith("dodaj"):
            if not target_id or not amount:
                await interaction.response.send_message("❌ Podaj target i kwotę.", ephemeral=True); return
            uid = str(target_id)
            ensure_user(db, uid)
            db["users"][uid]["ka"] = db["users"][uid].get("ka", 0) + int(amount)
            db["users"][uid]["earned_total"] = db["users"][uid].get("earned_total", 0) + int(amount)
            await write_db(db)
            await interaction.response.send_message(f"✅ Dodano {amount} KA do <@{target_id}>.", ephemeral=True)
            return
        if act in ("banuj", "ban"):
            member = interaction.guild.get_member(target_id) if interaction.guild and target_id else None
            if not member:
                await interaction.response.send_message("❌ Nie znaleziono członka na serwerze.", ephemeral=True); return
            try:
                await member.ban(reason=reason)
                await interaction.response.send_message(f"🚫 Zbanowano {member.mention}. Powód: {reason}", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Błąd banowania: {e}", ephemeral=True)
            return
        if act in ("ostrzez","ukarz","warn"):
            if not target_id:
                await interaction.response.send_message("❌ Podaj target.", ephemeral=True); return
            uid = str(target_id)
            ensure_user(db, uid)
            db["users"][uid]["warnings"] = db["users"][uid].get("warnings", 0) + 1
            await write_db(db)
            await interaction.response.send_message(f"⚠️ Dodano ostrzeżenie dla <@{target_id}>.", ephemeral=True)
            return
        if act in ("gildia_zmien","gildia"):
            if not target_id or not amount:
                await interaction.response.send_message("❌ Podaj target i nazwę gildii w polu 'Kwota' (tak, pole amount używamy jako nazwy gildii).", ephemeral=True); return
            uid = str(target_id)
            ensure_user(db, uid)
            db["users"][uid]["guild"] = amount
            await write_db(db)
            await interaction.response.send_message(f"🏰 Ustawiono gildie <@{target_id}> -> {amount}.", ephemeral=True)
            return

        await interaction.response.send_message("❌ Nieznana akcja admina.", ephemeral=True)

# Cog-level listener: route button clicks by custom_id -> _run_action_by_id
class PanelListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        # only handle component interactions (buttons)
        if not interaction.type.name.startswith("component"):
            return
        data = interaction.data or {}
        custom_id = data.get("custom_id") or data.get("id") or ""
        # find view instance by owner? simpler: if custom_id startswith "panel_" route it
        if custom_id.startswith("panel_"):
            # find the panel view (we can't easily access the original view instance),
            # so we create a temporary FullPanelView and dispatch action (owner check will block if not allowed)
            owner = interaction.user  # best-effort: allow only owner; if not owner, view will reject
            view = FullPanelView(self.bot, owner)
            # dispatch
            await view._run_action_by_id(interaction, custom_id)
        elif custom_id == "panel_admin":
            view = FullPanelView(self.bot, interaction.user)
            await view._open_admin_modal(interaction)
        # other custom ids handled by modals/view callbacks

async def setup(bot):
    # register two cogs: panel + listener
    await bot.add_cog(Panel(bot))
    await bot.add_cog(PanelListener(bot))
