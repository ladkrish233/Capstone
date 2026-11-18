import asyncio

from notebook.tools_demo import agent


async def main():
    async with agent.run_stream("Plan my day") as result:
        async for chunk in result.stream_text(delta=True):
            print(chunk, flush=True)
        print()


asyncio.run(main())
