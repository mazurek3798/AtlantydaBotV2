import asyncpg, os, time, random
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
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

async def get_guild_by_id(gid):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT id,name,leader,prestige,members_count FROM guilds WHERE id=$1', gid)
        return dict(row) if row else None

async def get_player_guild(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT guild_id, role FROM guild_members WHERE user_id=$1', user_id)
        return dict(row) if row else None

# Wars
async def create_war(guild_a, guild_b, start_ts, end_ts):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('INSERT INTO wars (guild_a,guild_b,start_ts,end_ts,wins_a,wins_b,active) VALUES($1,$2,$3,$4,0,0,TRUE) RETURNING id', guild_a, guild_b, start_ts, end_ts)
        return row['id']

async def get_active_wars(now_ts=None):
    if now_ts is None:
        now_ts = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM wars WHERE active=TRUE AND start_ts <= $1 AND end_ts >= $1', now_ts)
        return [dict(r) for r in rows]

async def increment_war_win(war_id, side):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if side=='a':
            await conn.execute('UPDATE wars SET wins_a = wins_a + 1 WHERE id=$1', war_id)
        else:
            await conn.execute('UPDATE wars SET wins_b = wins_b + 1 WHERE id=$1', war_id)

async def end_war(war_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        war = await conn.fetchrow('SELECT * FROM wars WHERE id=$1', war_id)
        if not war: return None
        await conn.execute('UPDATE wars SET active=FALSE WHERE id=$1', war_id)
        wa = war['wins_a']; wb = war['wins_b']; ga = war['guild_a']; gb = war['guild_b']
        if wa>wb:
            winner = ga; loser = gb
            await conn.execute('UPDATE guilds SET prestige = prestige + 10 WHERE id=$1', winner)
            rows = await conn.fetch('SELECT user_id FROM guild_members WHERE guild_id=$1', winner)
            for r in rows:
                uid = r['user_id']; bonus = 100 + wa*20
                await conn.execute('UPDATE players SET gold = gold + $1 WHERE user_id=$2', bonus, uid)
                if random.random() < 0.2:
                    await conn.execute('INSERT INTO inventory (user_id,item_id,qty) VALUES($1,$2,1) ON CONFLICT DO NOTHING', uid, 'victory_trophy')
            return {'winner':winner,'loser':loser,'wins':(wa,wb)}
        elif wb>wa:
            winner = gb; loser = ga
            await conn.execute('UPDATE guilds SET prestige = prestige + 10 WHERE id=$1', winner)
            rows = await conn.fetch('SELECT user_id FROM guild_members WHERE guild_id=$1', winner)
            for r in rows:
                uid = r['user_id']; bonus = 100 + wb*20
                await conn.execute('UPDATE players SET gold = gold + $1 WHERE user_id=$2', bonus, uid)
                if random.random() < 0.2:
                    await conn.execute('INSERT INTO inventory (user_id,item_id,qty) VALUES($1,$2,1) ON CONFLICT DO NOTHING', uid, 'victory_trophy')
            return {'winner':winner,'loser':loser,'wins':(wa,wb)}
        else:
            await conn.execute('UPDATE guilds SET prestige = prestige + 2 WHERE id IN ($1,$2)', ga, gb)
            return {'winner':None,'wins':(wa,wb)}
