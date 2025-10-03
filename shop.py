import discord
import math
import asyncio
import db_pg
import items

PAGE_SIZE = 20  # ile itemów na stronę

def make_item_option(it):
    label = f"{it['name']} (lvl {it.get('level',1)})"
    desc_parts = []
    if it.get('price') is not None:
        desc_parts.append(f"{it['price']}💧")
    if it.get('class'):
        desc_parts.append(it['class'])
    description = " • ".join(desc_parts)[:100]
    return discord.SelectOption(label=label[:100], value=it['id'], description=description)

# ======== Główne otwarcie sklepu ========
async def open_shop(interaction: discord.Interaction, user_id: int):
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        pass

    view = ShopCategoryView(user_id)
    await interaction.followup.send("🏪 Wybierz kategorię sklepu:", view=view, ephemeral=True)


# ======== Wybór kategorii ========
class ShopCategoryView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        options = [
            discord.SelectOption(label="Wszystkie", value="All", description="Pokaż wszystkie przedmioty"),
            discord.SelectOption(label="Wojownik", value="Wojownik"),
            discord.SelectOption(label="Zabójca", value="Zabójca"),
            discord.SelectOption(label="Mag", value="Mag"),
            discord.SelectOption(label="Kapłan", value="Kapłan"),
            discord.SelectOption(label="Mikstury", value="Mikstury"),
        ]
        self.add_item(ShopCategorySelect(options, user_id))

class ShopCategorySelect(discord.ui.Select):
    def __init__(self, options, user_id: int):
        super().__init__(placeholder="Wybierz kategorię...", options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)
        choice = self.values[0]

        # filtrowanie po klasie lub miksturach
        if choice == "All":
            filtered = items.ITEMS[:]
        elif choice == "Mikstury":
            filtered = [it for it in items.ITEMS if "potion" in it["id"]]
        else:
            filtered = [it for it in items.ITEMS if it.get('class') in (choice, 'All')]

        filtered.sort(key=lambda x: (x.get('level', 0), x.get('price', 0)))
        if not filtered:
            return await interaction.response.send_message("Brak przedmiotów w tej kategorii.", ephemeral=True)

        page = 0
        view = ShopItemsView(self.user_id, filtered, page)
        await interaction.followup.send(f"🛒 Sklep — {choice}", view=view, ephemeral=True)


# ======== Lista przedmiotów ========
class ShopItemsView(discord.ui.View):
    def __init__(self, user_id, items_list, page=0, timeout=180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.items_list = items_list
        self.page = page
        self.max_page = max(0, math.ceil(len(items_list) / PAGE_SIZE) - 1)

        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items_list[start:end]
        options = [make_item_option(it) for it in page_items]
        self.add_item(ShopItemSelect(options, user_id, self))

        if self.max_page > 0:
            self.add_item(PrevPageButton())
            self.add_item(NextPageButton())


class ShopItemSelect(discord.ui.Select):
    def __init__(self, options, user_id, parent_view):
        super().__init__(placeholder="Wybierz przedmiot...", options=options)
        self.user_id = user_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)

        item_id = self.values[0]
        item = next((it for it in items.ITEMS if it['id'] == item_id), None)
        if not item:
            return await interaction.followup.send("Nie znaleziono przedmiotu.", ephemeral=True)

        embed = discord.Embed(title=f"{item['name']}", color=discord.Color.gold())
        embed.add_field(name="Cena", value=f"{item.get('price', '?')}💧")
        embed.add_field(name="Poziom", value=f"{item.get('level', 1)}")
        embed.add_field(name="Klasa", value=item.get('class', 'All'))
        if item.get('special'):
            embed.add_field(name="Efekt", value=item['special'], inline=False)

        for stat in ('hp', 'str', 'dex', 'wis', 'cha'):
            if item.get(stat):
                embed.add_field(name=stat.upper(), value=str(item[stat]))

        await interaction.followup.send(embed=embed, view=BuyItemView(self.user_id, item_id), ephemeral=True)


# ======== Kupowanie ========
class BuyItemView(discord.ui.View):
    def __init__(self, user_id, item_id, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.item_id = item_id

    @discord.ui.button(label="Kup", style=discord.ButtonStyle.success)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Nie możesz kupić za kogoś innego.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)

        player = await db_pg.get_player(self.user_id)
        if not player:
            return await interaction.followup.send("Nie masz postaci!", ephemeral=True)

        item = next((it for it in items.ITEMS if it['id'] == self.item_id), None)
        if not item:
            return await interaction.followup.send("Przedmiot nie istnieje.", ephemeral=True)

        required_lvl = item.get('level', 1)
        price = item.get('price', 0)
        if player['level'] < required_lvl:
            return await interaction.followup.send(f"❌ Wymagany poziom: {required_lvl}.", ephemeral=True)
        if player['gold'] < price:
            return await interaction.followup.send(f"❌ Brakuje ci {price - player['gold']}💧.", ephemeral=True)

        # Kupno
        await db_pg.update_player(self.user_id, gold=player['gold'] - price)
        await db_pg.add_item(self.user_id, self.item_id, qty=1)

        # Efekty pasywne natychmiast
        await apply_item_effects(player, item, interaction)


# ======== Pasywne efekty i mikstury ========
async def apply_item_effects(player, item, interaction):
    """Nadaje bonusy po zakupie lub użyciu."""
    name = item['name']

    if "potion" in item['id']:
        await interaction.followup.send(f"🧪 Kupiono {name}! Mikstura automatycznie wyleczy cię w walce.", ephemeral=True)
        return

    desc = [f"✅ Kupiono **{name}** za {item['price']}💧"]
    bonuses = []

    if item.get('hp'):
        player['hp'] += item['hp']
        bonuses.append(f"+{item['hp']} HP")
    if item.get('str'):
        player['str'] += item['str']
        bonuses.append(f"+{item['str']} Siły")
    if item.get('dex'):
        player['dex'] += item['dex']
        bonuses.append(f"+{item['dex']} Zręczności")
    if item.get('wis'):
        player['wis'] += item['wis']
        bonuses.append(f"+{item['wis']} Mądrości")
    if item.get('cha'):
        player['cha'] += item['cha']
        bonuses.append(f"+{item['cha']} Charyzmy")

    if item.get('special'):
        bonuses.append(f"Specjalny efekt: {item['special']}")

    if bonuses:
        desc.append("Zyskano bonusy: " + ", ".join(bonuses))

    await interaction.followup.send("\n".join(desc), ephemeral=True)


# ======== Paginacja ========
class PrevPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="◀️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        parent: ShopItemsView = self.view
        if parent.page <= 0:
            return await interaction.response.send_message("Pierwsza strona.", ephemeral=True)
        parent.page -= 1
        await parent.update_page(interaction)

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="▶️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        parent: ShopItemsView = self.view
        if parent.page >= parent.max_page:
            return await interaction.response.send_message("Ostatnia strona.", ephemeral=True)
        parent.page += 1
        await parent.update_page(interaction)

async def auto_heal_check(player_id):
    """Sprawdza i używa mikstur, jeśli HP < 30%."""
    player = await db_pg.get_player(player_id)
    if not player:
        return

    if player['hp'] <= player['max_hp'] * 0.3:
        potions = await db_pg.get_inventory(player_id)
        potion = next((p for p in potions if "potion_hp" in p['item_id']), None)
        if potion:
            await db_pg.update_player(player_id, hp=player['max_hp'])
            await db_pg.remove_item(player_id, potion['item_id'], 1)
            print(f"💖 Autoheal dla gracza {player_id}")
