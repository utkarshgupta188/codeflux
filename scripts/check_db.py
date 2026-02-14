import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./local_dev.db"

async def check_logs():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        result = await session.execute(text("SELECT * FROM request_logs ORDER BY id DESC LIMIT 1"))
        row = result.fetchone()
        if row:
            print("Latest Log Entry:")
            # Access by index or name depending on row proxy
            print(f"ID: {row[0]}")
            print(f"Prompt: {row[1]}")
            print(f"Provider: {row[2]}")
            print(f"Model: {row[3]}")
            print(f"Latency: {row[4]}ms")
            print(f"Fallback Used: {row[5]}")
        else:
            print("No logs found.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_logs())
