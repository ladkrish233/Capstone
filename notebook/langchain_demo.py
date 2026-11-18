from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic

load_dotenv()


@tool
def get_time() -> str:
    """Return the current local time as HH:MM."""

    return datetime.now().strftime("%H:%m")


agent = create_agent(
    model=ChatAnthropic(model="claude-haiku-5-5"),
    tools=[get_time],
    system_prompt="You are a friendly assistant. Keep replies short.",
)


messages = []

while True:
    user = input("You : ")
    if user == "q":
        break
    messages.append({"role": "user", "content": user})
    result = agent.invoke({"messages": messages})
    messages = result["messages"]
    print(messages[-1].text)
