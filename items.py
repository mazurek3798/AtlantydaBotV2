import discord
import math
from typing import List
import items
import db_pg
import asyncio

# ---- Ustawienia ----
PAGE_SIZE = 20  # ile itemów pokazywać na jednej stronie (select max = 25)

# ---- Helper: przygotuj opcje SelectOption bez przekroczenia limitu długości ----
def make_item_option(it):
    label = f"{it['name']} (lvl {it.get('level',1)})"
    # SelectOption label max length is 100, description max 100
    desc_parts = []
    if it.get('price') is not None:
        desc_parts.append(f"{it['price']}💧")
    if it.get('class'):
        desc_parts.append(it['class'])
    description = " • ".join(desc_parts)[:100]
    return discord.SelectOption(label=label[:100], value=it['id'], description=description)

# ---- Główna funkcja do otwierania sklepu (wołać z MainPanelView) ----
async def open_shop(interaction: discord.Interaction, user_id: int):
    """
    Otwiera widok wyboru kategorii, potem pokazuje listę przedmiotów i pozwala kupić.
    Wywołanie: await shop.open_shop(interaction, user_id)
    """
    # natychmiast od razu zareaguj (defer) — aby nie wywaliło "This interaction failed"
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        # jeśli już odpowiedziano, ignorujemy
        pass

    view = ShopCategoryView(user_id)
    # zamiast wysyłać publicznie, odpowiadamy ephemeral (user tylko widzi)
    try:
        await interaction.followup.send("🛒 Wybierz kategorię sklepu:", view=view, ephemeral=True)
    except Exception:
        # fallback: response if followup fails
        try:
            await interaction.response.send_message("🛒 Wybierz kategorię sklepu:", view=view, ephemeral=True)
        except Exception as e:
            print("shop.open_shop send error:", e)

# ---- Widok wyboru kategorii ----
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
        ]
        self.add_item(ShopCategorySelect(options, user_id))

class ShopCategorySelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], user_id: int):
        super().__init__(placeholder="Wybierz kategorię...", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)
        choice = self.values[0]
        # filtrowanie przedmiotów
        if choice == "All":
            filtered = items.ITEMS[:]
        else:
            filtered = [it for it in items.ITEMS if it.get('class') in (choice, 'All')]
        # sortowanie: level asc then price asc
        filtered.sort(key=lambda x: (x.get('level', 0), x.get('price', 0)))
        if not filtered:
            return await interaction.response.send_message("Brak przedmiotów w tej kategorii.", ephemeral=True)
        # paginacja: pokaż pierwszą stronę
        page = 0
        view = ShopItemsView(self.user_id, filtered, page=page)
        # użyj followup bo przed chwilą deferowaliśmy
        await interaction.followup.send(f"🛒 Sklep — kategoria: **{choice}** (strona {page+1}/{max(1, math.ceil(len(filtered)/PAGE_SIZE))})", view=view, ephemeral=True)

# ---- Widok listy przedmiotów + paginacja ----
class ShopItemsView(discord.ui.View):
    def __init__(self, user_id: int, items_list: List[dict], page: int = 0, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.items_list = items_list
        self.page = page
        self.max_page = max(0, math.ceil(len(items_list) / PAGE_SIZE) - 1)

        # build select with items for the current page
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items_list[start:end]
        options = [make_item_option(it) for it in page_items]
        self.add_item(ShopItemSelect(options, user_id, self))

        # add pagination buttons if needed
        if self.max_page > 0:
            self.add_item(PrevPageButton())
            self.add_item(NextPageButton())

class ShopItemSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], user_id: int, parent_view: ShopItemsView):
        super().__init__(placeholder="Wybierz przedmiot, aby zobaczyć szczegóły i kupić...", min_values=1, max_values=1, options=options)
        self.user_id = user_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # owner check
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)

        # defer (we may run DB ops)
        await interaction.response.defer(ephemeral=True)

        item_id = self.values[0]
        item = next((it for it in items.ITEMS if it['id'] == item_id), None)
        if not item:
            return await interaction.followup.send("Nie znaleziono przedmiotu.", ephemeral=True)

        # show details and prompt to buy with Buy button
        embed = discord.Embed(title=f"🛒 {item['name']}", color=discord.Color.gold())
        desc_lines = []
        desc_lines.append(f"ID: `{item['id']}`")
        desc_lines.append(f"Klasa: {item.get('class','All')}")
        desc_lines.append(f"Poziom wymagany: {item.get('level',1)}")
        desc_lines.append(f"Cena: {item.get('price','?')}💧")
        # staty
        for stat in ('hp','str','dex','wis','cha'):
            if item.get(stat):
                desc_lines.append(f"{stat.upper()}: {item.get(stat)}")
        if item.get('special'):
            desc_lines.append(f"Specjalne: {item.get('special')}")
        embed.description = "\n".join(desc_lines)

        # buy view with a Buy button
        buy_view = BuyItemView(self.user_id, item_id)
        await interaction.followup.send(embed=embed, view=buy_view, ephemeral=True)

# ---- Buy button + logic ----
class BuyItemView(discord.ui.View):
    def __init__(self, user_id: int, item_id: str, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.item_id = item_id

    @discord.ui.button(label="Kup", style=discord.ButtonStyle.success)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("To nie jest Twoja transakcja.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # fetch player
        player = await db_pg.get_player(self.user_id)
        if not player:
            return await interaction.followup.send("Nie masz postaci. Stwórz postać, zanim kupisz.", ephemeral=True)

        item = next((it for it in items.ITEMS if it['id'] == self.item_id), None)
        if not item:
            return await interaction.followup.send("Przedmiot już nie istnieje.", ephemeral=True)

        # level & gold checks
        required_lvl = item.get('level',1)
        price = item.get('price', 0)
        if player['level'] < required_lvl:
            return await interaction.followup.send(f"Potrzebujesz poziomu {required_lvl} aby kupić ten przedmiot.", ephemeral=True)
        if player['gold'] < price:
            return await interaction.followup.send(f"Nie masz wystarczająco złota. Potrzebujesz {price}💧.", ephemeral=True)

        # perform purchase
        try:
            # update gold and add item (transaction-like)
            await db_pg.update_player(self.user_id, gold=player['gold'] - price)
            await db_pg.add_item(self.user_id, self.item_id, qty=1)
            # optionally: give immediate stat bonuses? (we just store item in inventory)
            await interaction.followup.send(f"✅ Kupiono **{item['name']}** za {price}💧. Sprawdź swój ekwipunek.", ephemeral=True)
        except Exception as e:
            # rollback is not implemented — inform user
            await interaction.followup.send(f"❌ Błąd podczas zakupu: {e}", ephemeral=True)

# ---- Pagination buttons ----
class PrevPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀️ Poprzednia", disabled=False)

    async def callback(self, interaction: discord.Interaction):
        # parent view is ShopItemsView
        parent: ShopItemsView = self.view
        if interaction.user.id != parent.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)
        if parent.page <= 0:
            return await interaction.response.send_message("Jesteś na pierwszej stronie.", ephemeral=True)
        parent.page -= 1
        # rebuild view: replace select options
        start = parent.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = parent.items_list[start:end]
        parent.clear_items()
        parent.add_item(ShopItemSelect([make_item_option(it) for it in page_items], parent.user_id, parent))
        parent.add_item(PrevPageButton())
        parent.add_item(NextPageButton())
        # edit original message if possible
        try:
            await interaction.response.edit_message(content=f"🛒 Strona {parent.page+1}/{parent.max_page+1}", view=parent)
        except Exception:
            await interaction.followup.send(f"🛒 Strona {parent.page+1}/{parent.max_page+1}", view=parent, ephemeral=True)

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Następna ▶️", disabled=False)

    async def callback(self, interaction: discord.Interaction):
        parent: ShopItemsView = self.view
        if interaction.user.id != parent.user_id:
            return await interaction.response.send_message("To nie jest Twój sklep.", ephemeral=True)
        if parent.page >= parent.max_page:
            return await interaction.response.send_message("Jesteś na ostatniej stronie.", ephemeral=True)
        parent.page += 1
        start = parent.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = parent.items_list[start:end]
        parent.clear_items()
        parent.add_item(ShopItemSelect([make_item_option(it) for it in page_items], parent.user_id, parent))
        parent.add_item(PrevPageButton())
        parent.add_item(NextPageButton())
        try:
            await interaction.response.edit_message(content=f"🛒 Strona {parent.page+1}/{parent.max_page+1}", view=parent)
        except Exception:
            await interaction.followup.send(f"🛒 Strona {parent.page+1}/{parent.max_page+1}", view=parent, ephemeral=True)
