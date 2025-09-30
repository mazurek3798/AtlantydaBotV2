import aiosqlite

async def init_db():
    async with aiosqlite.connect("atlantyda.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT,
            class TEXT,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 0,
            strength INTEGER DEFAULT 0,
            dexterity INTEGER DEFAULT 0,
            wisdom INTEGER DEFAULT 0,
            charisma INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gold INTEGER DEFAULT 0,
            prestige INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS war_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER DEFAULT 0,
            player_id INTEGER,
            points INTEGER,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()
