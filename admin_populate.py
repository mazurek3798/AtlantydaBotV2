import asyncio
import db

async def populate():
    await db.init_db()
    print("Dodano przykładowe dane do testów")

if __name__ == "__main__":
    asyncio.run(populate())
