from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv()

agent = Agent(
    "openrouter:deepseek/deepseek-chat",
    instructions="My name is Krishna",
    model_settings={"temperature": 0},
)

result = agent.run_sync("what is my name")
print(result.output)
print(result.usage)
