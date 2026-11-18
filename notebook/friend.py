import asyncio

from app.cost import run_cost
from app.db import add_cost_event
from notebook.tools_demo import agent


async def main():
    message = []
    while True:
        user_input = input("You : ")
        if user_input == "q":
            break
        async with agent.run_stream(user_input, message_history=message) as result:
            async for chunk in result.stream_text(delta=True):
                print(chunk, end="", flush=True)
            print()
        message += result.new_messages()
        add_cost_event(
            model=result.response.model_name,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cost_usd=run_cost(result.usage),
        )


asyncio.run(main())
