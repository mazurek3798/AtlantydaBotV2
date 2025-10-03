# items.py — lista wszystkich przedmiotów dostępnych w świecie Atlantydy 🌊

ITEMS = [
    # ====== NEUTRALNE ======
    {
        "id": "basic_potion",
        "name": "Mikstura Życia (Mała)",
        "class": "All",
        "price": 25,
        "level": 1,
        "potion": 50,  # leczy 50 HP
        "special": "Odnawia 50 punktów życia podczas użycia."
    },
    {
        "id": "greater_potion",
        "name": "Mikstura Życia (Duża)",
        "class": "All",
        "price": 60,
        "level": 3,
        "potion": 150,
        "special": "Odnawia 150 punktów życia podczas użycia."
    },
    {
        "id": "elixir_vitality",
        "name": "Eliksir Witalności",
        "class": "All",
        "price": 120,
        "level": 5,
        "potion": 300,
        "hp": 20,
        "special": "Stały bonus +20 HP po wypiciu."
    },

    # ====== WOJOWNIK ======
    {
        "id": "iron_sword",
        "name": "Żelazny Miecz",
        "class": "Wojownik",
        "price": 80,
        "level": 2,
        "str": 5,
        "special": "Podstawowa broń wojownika, dodaje 5 siły."
    },
    {
        "id": "steel_armor",
        "name": "Stalowa Zbroja",
        "class": "Wojownik",
        "price": 150,
        "level": 4,
        "hp": 40,
        "str": 2,
        "special": "Zwiększa wytrzymałość i lekko siłę."
    },
    {
        "id": "blade_of_valor",
        "name": "Ostrze Odwagi",
        "class": "Wojownik",
        "price": 300,
        "level": 6,
        "str": 10,
        "hp": 25,
        "special": "Broń legendarna. Posiadacz zyskuje pasywnie +10 STR i +25 HP."
    },

    # ====== ZABÓJCA ======
    {
        "id": "dagger_shadow",
        "name": "Sztylet Cienia",
        "class": "Zabójca",
        "price": 70,
        "level": 2,
        "dex": 6,
        "special": "Zwiększa zręczność, idealny do skrytobójstw."
    },
    {
        "id": "cloak_night",
        "name": "Płaszcz Nocy",
        "class": "Zabójca",
        "price": 130,
        "level": 4,
        "dex": 4,
        "cha": 3,
        "special": "Zwiększa zręczność i charyzmę w misjach szpiegowskich."
    },
    {
        "id": "fangs_serpent",
        "name": "Kły Węża",
        "class": "Zabójca",
        "price": 250,
        "level": 6,
        "dex": 9,
        "wis": 4,
        "special": "Unikalne ostrza zatrute jadem. +9 DEX, +4 WIS."
    },

    # ====== MAG ======
    {
        "id": "magic_staff",
        "name": "Laska Ucznia",
        "class": "Mag",
        "price": 75,
        "level": 2,
        "wis": 6,
        "special": "Podstawowa laska magiczna. +6 mądrości."
    },
    {
        "id": "robe_arcana",
        "name": "Szata Arkanów",
        "class": "Mag",
        "price": 160,
        "level": 4,
        "hp": 20,
        "wis": 8,
        "special": "Szata wzmacniająca magię. +8 WIS, +20 HP."
    },
    {
        "id": "orb_ancients",
        "name": "Kula Pradawnych",
        "class": "Mag",
        "price": 300,
        "level": 6,
        "wis": 12,
        "cha": 6,
        "special": "Relikt dawnych magów. +12 WIS, +6 CHA."
    },

    # ====== KAPŁAN ======
    {
        "id": "blessed_symbol",
        "name": "Błogosławiony Symbol",
        "class": "Kapłan",
        "price": 70,
        "level": 2,
        "wis": 5,
        "cha": 2,
        "special": "Święty amulet, dodaje mądrość i charyzmę."
    },
    {
        "id": "robes_faith",
        "name": "Szaty Wiary",
        "class": "Kapłan",
        "price": 140,
        "level": 4,
        "hp": 25,
        "wis": 6,
        "special": "Zwiększa HP i mądrość kapłana."
    },
    {
        "id": "light_relic",
        "name": "Relikt Światła",
        "class": "Kapłan",
        "price": 280,
        "level": 6,
        "wis": 10,
        "cha": 8,
        "special": "Potężny artefakt boskiej mocy. +10 WIS, +8 CHA."
    },

    # ====== RZADKIE / ARTEFAKTY ======
    {
        "id": "ring_eternity",
        "name": "Pierścień Wieczności",
        "class": "All",
        "price": 500,
        "level": 8,
        "hp": 50,
        "wis": 10,
        "special": "Unikalny pierścień wzmacniający żywotność i mądrość."
    },
    {
        "id": "phoenix_potion",
        "name": "Eliksir Feniksa",
        "class": "All",
        "price": 450,
        "level": 7,
        "potion": 1000,
        "special": "Odnawia 1000 HP i wskrzesza po śmierci (jednorazowo)."
    },
]
