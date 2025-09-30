
# Atlantyda RPG — Complete Ready Package

This package is the completed, modular, ready-to-deploy Atlantyda RPG Discord bot.

How to use:
1. Copy `.env.example` to `.env` and set DISCORD_TOKEN and OWNER_ID.
2. Create virtualenv, install requirements.
3. Run `python bot.py` or use Docker via provided Dockerfile/docker-compose.

All game commands live in `cogs/rpg.py` and are registered as slash commands:
- /start, /profil, /statystyki, /ekwipunek, /sklep, /kup, /trening, /misja, /pojedynki, /handel, /gildia, /ranking, /admin

Database: `atlantyda.db` will be created in the package root on first run.

Notes:
- Review admin perms and owner configuration.
- For production, consider migrating SQLite to a managed DB and securing backups.
