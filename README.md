# AtlantydaBot v2 - Grywalna wersja

Instrukcja uruchomienia:
1. Utwórz virtualenv: `python -m venv venv && source venv/bin/activate` (Linux/macOS) lub `venv\Scripts\activate` (Windows)
2. Zainstaluj zależności: `pip install -r requirements.txt`
3. Ustaw zmienną środowiskową `DISCORD_TOKEN` z tokenem bota.
4. Uruchom: `python bot.py`

Zmiany w v2:
- System RP (listener on_message) — nagrody za RP ≥120 znaków raz na 24h.
- Rozszerzone eventy z unikalnymi mechanikami (Kraken, Skarb Posejdona, Festiwal Syren).
- Rozbudowane gildie: skarbiec, questy gildyjne, premie.
- Więcej przedmiotów w sklepie, pasywne efekty i jednorazowe buffy.
- System rang, odznak i sezonowy ranking.
- Daily/admin reports i narzędzia balansu.

Uwaga: Bot reaguje TYLKO na kanale o nazwie 'Atlantyda'.

Dodatkowo w wersji v2:
- Tygodniowe questy osobiste (/tygodniowy_quest i /claim_quest)
- Tygodniowe cele gildii (ustawiane przez właściciela)
- Ulepszone potwierdzenia (embedy) oraz tygodniowy raport wysyłany na kanale Atlantyda.
