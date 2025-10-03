import asyncpg
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()

# ⬇️ PRAWIDŁOWE pobranie URL bazy danych
DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise ValueError("❌ Brak zmiennej DATABASE_URL! Ustaw ją w Railway Variables.")
        print(f"🔗 Łączenie z bazą: {DATABASE_URL}")
        _pool = await asyncpg.create_pool(DATABASE_URL, max_size=10)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            class TEXT,
            level INT DEFAULT 1,
            xp INT DEFAULT 0,
            gold INT DEFAULT 100,
            hp INT,
            max_hp INT,
            str INT DEFAULT 0,
            dex INT DEFAULT 0,
            wis INT DEFAULT 0,
            cha INT DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            item_id TEXT,
            qty INT DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS guilds (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE,
            leader BIGINT,
            members_count INT DEFAULT 1,
            prestige INT DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS guild_members (
            guild_id INT,
            user_id BIGINT,
            role TEXT,
            PRIMARY KEY (guild_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS wars (
            id SERIAL PRIMARY KEY,
            guild_a INT,
            guild_b INT,
            start_ts BIGINT,
            end_ts BIGINT,
            wins_a INT DEFAULT 0,
            wins_b INT DEFAULT 0,
            active BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            name TEXT,
            effect TEXT,
            start_ts BIGINT,
            duration INT
        );
        """)
        print("✅ Baza danych zainicjalizowana!")

# Players
async def create_player(user_id, name, klass, stats, gold=150):
    pool = await get_pool()
    max_hp = 20 + stats.get('hp_bonus',0)
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO players(user_id,name,class,level,xp,gold,hp,max_hp,str,dex,wis,cha)
        VALUES($1,$2,$3,1,0,$4,$5,$5,$6,$7,$8,$9)
        ON CONFLICT(user_id) DO NOTHING
        """, user_id, name, klass, gold, max_hp, stats.get('str',0), stats.get('dex',0), stats.get('wis',0), stats.get('cha',0))

async def get_player(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM players WHERE user_id=$1', user_id)
        return dict(row) if row else None

async def update_player(user_id, **kwargs):
    if not kwargs: return
    pool = await get_pool()
    keys = list(kwargs.keys())
    vals = [kwargs[k] for k in keys]
    sets = ','.join([f"{k}=${i+1}" for i,k in enumerate(keys)])
    sql = f'UPDATE players SET {sets} WHERE user_id=${len(keys)+1}'
    async with pool.acquire() as conn:
        await conn.execute(sql, *vals, user_id)

# Inventory
async def add_item(user_id, item_id, qty=1):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT id, qty FROM inventory WHERE user_id=$1 AND item_id=$2', user_id, item_id)
        if row:
            await conn.execute('UPDATE inventory SET qty = qty + $1 WHERE id=$2', qty, row['id'])
        else:
            await conn.execute('INSERT INTO inventory (user_id,item_id,qty) VALUES($1,$2,$3)', user_id, item_id, qty)

async def get_inventory(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT item_id, qty FROM inventory WHERE user_id=$1', user_id)
        return [dict(r) for r in rows]

# Guilds
async def create_guild(name, leader_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO guilds(name,leader,members_count,prestige) VALUES($1,$2,1,0)', name, leader_id)
        row = await conn.fetchrow('SELECT id FROM guilds WHERE name=$1', name)
        gid = row['id']
        await conn.execute('INSERT INTO guild_members (guild_id,user_id,role) VALUES($1,$2,$3)', gid, leader_id, 'Mistrz')
        return gid

async def join_guild(guild_id, user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO guild_members (guild_id,user_id,role) VALUES($1,$2,$3) ON CONFLICT DO NOTHING', guild_id, user_id, 'Członek')
        await conn.execute('UPDATE guilds SET members_count = members_count + 1 WHERE id=$1', guild_id)

async def get_guild_by_name(name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM guilds WHERE name=$1', name)
        return dict(row) if row else None

async def get_guild_by_id(_
