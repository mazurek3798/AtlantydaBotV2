import sqlite3

def migrate(db_path="atlantyda.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(war_logs)")
        cols = [col[1] for col in c.fetchall()]
        if "guild_id" not in cols:
            print("Migracja: dodaję kolumnę guild_id do war_logs")
            c.execute("ALTER TABLE war_logs ADD COLUMN guild_id INTEGER DEFAULT 0")
            conn.commit()
        else:
            print("Migracja: war_logs już ma guild_id")
    except Exception as e:
        print("Błąd migracji:", e)
    conn.close()
