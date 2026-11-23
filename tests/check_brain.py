from dotenv import load_dotenv
import asyncio
from app.harness.brain import Brain
from app.pool import make_pool

load_dotenv()

async def main():
    pool=await make_pool()
    brain=Brain(pool)
    r1 = await brain.ask("my name is krishna")
    print(r1.output)

    brain2=Brain(pool)
    r2=await brain2.ask("what is my name")
    print(r2.output)

    await pool.close()

asyncio.run(main())