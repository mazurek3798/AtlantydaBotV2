# 🌊 Atlantyda RPG — Full Playable Bot (Railway + PostgreSQL)

This package contains a playable Discord RPG bot ready to run on Railway with a PostgreSQL addon.

## What's included
- `bot.py` — main bot: commands, interactions, PvE/PvP, shop, guilds, wars, hourly events
- `db_pg.py` — PostgreSQL data layer (asyncpg)
- `items.py` — full item database from your blueprint
- `guide.py` — interactive guide embed with buttons (Profile, Shop, Guilds, Ranking)
- `Procfile`, `.env.example`, `requirements.txt`, `README.md`

## Quick Railway deploy
1. Create a new Railway project and connect repository or upload these files.
2. Add a PostgreSQL plugin (Railway → Plugins → PostgreSQL). Railway will give you `DATABASE_URL`.
3. In Project Settings → Environment, add variables:
   - `TOKEN` (Discord bot token)
   - `ATLANTYDA_CHANNEL_ID` (channel ID, number)
   - `DATABASE_URL` (from Railway plugin)
4. Deploy. Railway runs `worker: python bot.py` (Procfile).
5. After start, the bot will create DB tables automatically. Open your Discord server's specified channel and use `!start` to create a character.

## Commands (prefix `!`)
- `!start` — create character (interactive)
- `!panel` — show player profile
- `!pve` — fight a PvE encounter
- `!pvp @user [stake]` — challenge a player
- `!shop` — view shop
- `!buy <item_id>` — buy item
- `!guild create <name>` / `!guild join <name>` / `!guild war <name>` — guild management
- `!guide` — show interactive guide embed
- `!ranking` — show top players and guilds

## Notes
- All gameplay commands are limited to the channel set in `ATLANTYDA_CHANNEL_ID`.
- Hourly events are announced on the game channel and affect the gameplay.
- Guild wars last 3 days; PvP wins between members of warring guilds increment war points.
- This is a solid MVP ready for expansion: balance tweaks, new items, quests, cooldowns, images.

If you want, I can also:
- walk you step-by-step through adding the Railway PostgreSQL plugin and the environment variables in the Railway UI,
- extend balancing, add cooldowns, or create a Discord message that explains the game to new players.
