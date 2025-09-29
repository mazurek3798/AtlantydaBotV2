# cogs/utils.py
import json
import os
import tempfile
import asyncio
import time

BASE = os.path.dirname(os.path.dirname(__file__))  # project root
DB_PATH = os.path.join(BASE, "database.json")
LOCK = asyncio.Lock()

def atomic_write(path: str, data: str):
    dirn = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirn)
    with os.fdopen(fd, "w", encoding="utf-8") as w:
        w.write(data)
    os.replace(tmp, path)

async def read_db():
    async with LOCK:
        if not os.path.exists(DB_PATH):
            atomic_write(DB_PATH, json.dumps({"users": {}, "admin_logs": []}, ensure_ascii=False, indent=2))
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

async def write_db(obj):
    async with LOCK:
        atomic_write(DB_PATH, json.dumps(obj, ensure_ascii=False, indent=2))

def ensure_user(db, user_id: str):
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "ka": 0,
            "earned_total": 0,
            "spent_total": 0,
            "last_work": 0,
            "level": 0,
            "xp": 0,
            "reputation": 0,
            "items": {},
            "badges": [],
            "warnings": 0
        }

def channel_check(channel):
    return channel and channel.name.lower() == "atlantyda"

def level_from_xp(xp: int):
    # Simple leveling: every 100 xp = 1 level (tweakable)
    return xp // 100

def add_admin_log(db, actor_id: int, action: str, target_id: int | None = None, info: str | None = None):
    if "admin_logs" not in db:
        db["admin_logs"] = []
    db["admin_logs"].append({
        "time": int(time.time()),
        "actor": actor_id,
        "action": action,
        "target": target_id,
        "info": info
    })
