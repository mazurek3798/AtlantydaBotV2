import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def connect():
    return await asyncpg.connect(DATABASE_URL)

async def setup_db():
    conn = await connect()
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        user_id BIGINT UNIQUE,
        name TEXT,
        level INT DEFAULT 1,
        hp INT DEFAULT 20,
        gold INT DEFAULT 0,
        strength INT DEFAULT 0,
        dexterity INT DEFAULT 0,
        wisdom INT DEFAULT 0,
        charisma INT DEFAULT 0,
        guild_id INT
    );
    CREATE TABLE IF NOT EXISTS guilds (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        master_id BIGINT
    );
    CREATE TABLE IF NOT EXISTS wars (
        id SERIAL PRIMARY KEY,
        guild1 INT,
        guild2 INT,
        points1 INT DEFAULT 0,
        points2 INT DEFAULT 0,
        ends_at TIMESTAMP
    );
    """)
    await conn.close()

async def get_player(user_id):
    conn = await connect()
    player = await conn.fetchrow("SELECT * FROM players WHERE user_id=$1", user_id)
    await conn.close()
    return player
