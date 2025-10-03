import discord
import math
from typing import List
import asyncio
import items
import db_pg

PAGE_SIZE = 20  # max 25 dla selecta Discorda

# ---- Helper: SelectOption ----
def make_item_option(it):
    label = f"{it['name']} (lvl {it.get('level',1)})"
    desc = []
    if it.get('price') is not None:
        desc.append(f"{it['price']}💧")
    if it.get('class'):
        desc.append(it['class'])
    description = " • ".join(desc)[:100]
    return discord.SelectOption(label=label[:100], value=it['id'], description=description)

# ---- Główna funkcja ----
async def open_shop(interaction: discord.Interaction, user_id: int):
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        pass

    # pobierz dane gracza z bazy
    player = await db_pg.get_player(user_id)
    if not player:
        return await interaction.followup.send(
            "⚠️ Nie masz jeszcze postaci! Stwórz ją w panelu głównym.",
            ephemeral=True
        )

    player_class = player.get('class', 'All')

    # filtrowanie przedmiotów
    filtered = [it for it in items.ITEMS if it.get('class') in (player_class, 'All')]
    filtered.sort(key=lambda x: (x.get('level', 0), x.get('price', 0)))

    if not filtered:
        return await interaction.followup.send(
            f"🛒 Brak przedmiotów dla klasy **{player_class}**.",
            ephemeral=True
        )

    view = ShopItemsView(user_id, filtered, player_class)
    await interaction.followup.send(
        f"🛒 Sklep — przedmioty dla klasy **{player_class}**",
        view=view,
        ephemeral=True
    )

# ---- Widok listy ----
class ShopItemsView(discord.ui.View):
    def __init__(self, user_id: int, items_list: List[dict], player_class: str, page: int = 0, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.items_list = items_list
        self.player_class = player_class
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
    def __init__(self, options: List[discord.SelectOption], user_id: int, parent_view: ShopItemsView):
        super().__init__(placeholder="Wybierz przedmiot do podglądu...", min_values=1, max_values=1, options=options)
        self.user_id = user_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("⛔ To nie jest Twój sklep.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        item_id = self.values[0]
        item = next((it for it in items.ITEMS if it['id'] == item_id), None)
        if not item:
            return await interaction.followup.send("❌ Przedmiot nie istnieje.", ephemeral=True)

        embed = discord.Embed(title=f"🛒 {item['name']}", color=discord.Color.gold())
        desc = [
            f"**ID:** `{item['id']}`",
            f"**Klasa:** {item.get('class', 'All')}",
            f"**Poziom:** {item.get('level', 1)}",
            f"**Cena:** {item.get('price', '?')}💧"
        ]

        # Statystyki
        for stat in ('hp', 'str', 'dex', 'wis', 'cha'):
            if item.get(stat):
                desc.append(f"**{stat.upper()}:** {item.get(stat)}")

        if item.get('special'):
            desc.append(f"✨ **Specjalne:** {item['special']}")
        if item.get('potion'):
            desc.append(f"🧪 **Typ:** Mikstura życia ({item['potion']} HP)")

        embed.description = "\n".join(desc)

        view = BuyItemView(self.user_id, item_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ---- Kupno przedmiotu ----
class BuyItemView(discord.ui.View):
    def __init__(self, user_id: int, item_id: str, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.item_id = item_id

    @discord.ui.button(label="Kup przedmiot", style=discord.ButtonStyle.success)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("⛔ To nie jest Twoja transakcja.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        player = await db_pg.get_player(self.user_id)
        if not player:
            return await interaction.followup.send("Nie masz postaci.", ephemeral=True)

        item = next((it for it in items.ITEMS if it['id'] == self.item_id), None)
        if not item:
            return await interaction.followup.send("❌ Ten przedmiot już nie istnieje.", ephemeral=True)

        lvl_req = item.get('level', 1)
        price = item.get('price', 0)

        if player['level'] < lvl_req:
            return await interaction.followup.send(f"❌ Potrzebujesz poziomu {lvl_req}.", ephemeral=True)
        if player['gold'] < price:
            return await interaction.followup.send(f"❌ Nie masz {price}💧.", ephemeral=True)

        try:
            # odejmij złoto
            await db_pg.update_player(self.user_id, gold=player['gold'] - price)
            # dodaj przedmiot
            await db_pg.add_item(self.user_id, self.item_id, qty=1)

            msg = f"✅ Kupiono **{item['name']}** za {price}💧!"

            # pasywne bonusy natychmiast
            bonuses = []
            for stat in ('hp', 'str', 'dex', 'wis', 'cha'):
                if item.get(stat):
                    await db_pg.update_player(
                        self.user_id,
                        **{stat: player.get(stat, 0) + item[stat]}
                    )
                    bonuses.append(f"+{item[stat]} {stat.upper()}")

            if bonuses:
                msg += "\n📈 Pasywne bonusy: " + ", ".join(bonuses)

            # automatyczne mikstury
            if item.get('potion'):
                await db_pg.add_item(self.user_id, self.item_id, qty=2)
                msg += f"\n🧪 Otrzymano też 2 mikstury życia ({item['potion']} HP każda)."

            await interaction.followup.send(msg, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Błąd podczas zakupu: {e}", ephemeral=True)

# ---- Paginacja ----
class PrevPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀️ Poprzednia")

    async def callback(self, interaction: discord.Interaction):
        parent: ShopItemsView = self.view
        if interaction.user.id != parent.user_id:
            return await interaction.response.send_message("To nie Twój sklep.", ephemeral=True)
        if parent.page <= 0:
            return await interaction.response.send_message("Pierwsza strona.", ephemeral=True)

        parent.page -= 1
        await self.update_page(interaction, parent)

    async def update_page(self, interaction, parent):
        start = parent.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = parent.items_list[start:end]
        parent.clear_items()
        parent.add_item(ShopItemSelect([make_item_option(it) for it in page_items], parent.user_id, parent))
        parent.add_item(PrevPageButton())
        parent.add_item(NextPageButton())
        await interaction.response.edit_message(
            content=f"🛒 Sklep — {parent.page+1}/{parent.max_page+1} (klasa {parent.player_class})",
            view=parent
        )

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Następna ▶️")

    async def callback(self, interaction: discord.Interaction):
        parent: ShopItemsView = self.view
        if interaction.user.id != parent.user_id:
            return await interaction.response.send_message("To nie Twój sklep.", ephemeral=True)
        if parent.page >= parent.max_page:
            return await interaction.response.send_message("Ostatnia strona.", ephemeral=True)

        parent.page += 1
        await self.update_page(interaction, parent)

    async def update_page(self, interaction, parent):
        start = parent.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = parent.items_list[start:end]
        parent.clear_items()
        parent.add_item(ShopItemSelect([make_item_option(it) for it in page_items], parent.user_id, parent))
        parent.add_item(PrevPageButton())
        parent.add_item(NextPageButton())
        await interaction.response.edit_message(
            content=f"🛒 Sklep — {parent.page+1}/{parent.max_page+1} (klasa {parent.player_class})",
            view=parent
        )
