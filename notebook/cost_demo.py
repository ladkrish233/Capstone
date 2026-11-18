from app.cost import run_cost
from app.db import add_cost_event
from notebook.tools_demo import agent

result = agent.run_sync("Plan but day")
print(result.output)
print(result.usage)
print("Cost in Dollars: ", run_cost(result.usage))

add_cost_event(
    model=result.response.model_name,
    input_tokens=result.usage.input_tokens,
    output_tokens=result.usage.output_tokens,
    cost_usd=run_cost(result.usage),
)
