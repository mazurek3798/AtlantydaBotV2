import json, os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.json")

def read_db():
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_db(obj):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def ensure_user(db, user_id: str):
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "ka": 0,
            "level": 0,
            "reputation": 0,
            "items": {},
            "daily": 0,
            "work": 0,
            "explore": 0,
            "steal_count": 0,
            "last_rp_reward": 0,
            "earned_total": 0,
            "spent_total": 0,
            "badges": [],
            "rp_xp": 0
        }

def channel_check(channel):
    return channel and channel.name == "Atlantyda"

def level_from_ka(to
