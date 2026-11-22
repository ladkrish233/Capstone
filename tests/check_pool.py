import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.pool import make_pool

async def main():
    pool=await make_pool()
    print(await pool.fetchval("select 1"))
    await pool.close()

asyncio.run(main())