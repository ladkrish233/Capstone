from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.capabilities import ModelFallback

load_dotenv()

agent = Agent(
    "openrouter:deepseek/deepseerchat",
    instructions="You are a friendly assistant. Keep replies short.",
    model_settings={"timeout": 20},
    capabilities=[ModelFallback("anthropic:claude-haiku-5-5")],
)

result = agent.run_sync("Say hello in one sentence.")
print(result.output)
