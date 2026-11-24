from decimal import Decimal

from pydantic_ai_harness import DetectLoops
from pydantic_ai_harness.repair_tool_arguments import RepairToolArguments
from pydantic_ai_harness.spend import PostgresSpendStore,Budget,SpendLimits
from pydantic_ai_harness.step_persistence import StepPersistence
from pydantic_ai_harness.tool_output_limits import (
    Band,
    ToolOutputLimits,
    Truncate,
    Summarize,
    Spill
)
from app.harness.spillstore import PostgresSpillStore


def build_capabilities(store,pool):
    return [
        StepPersistence(store,agent_name="friend"),
        ToolOutputLimits(
            bands=[
                Band(over=100_000,action=Spill(then=Truncate())),
                Band(over=20_000,action=Summarize(then=Truncate())),
                Band(over=5000,action=Truncate(max_chars=5_000))
                ],
                store=PostgresSpillStore(pool)
            ),
        RepairToolArguments(),
        DetectLoops(repeated_call_threshold=3),
        SpendLimits(
            budgets=[
                Budget(usd=Decimal("1.00"),window="run",name="per_message"),
                Budget(usd=Decimal("2.00"),window="day",tokens=900_000,warn_at=1.5),

            ],
            store  = PostgresSpendStore(pool,table="friend-spend"),
            )
        ]