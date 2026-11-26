import logging

from decimal import Decimal

from pydantic_ai_harness import DetectLoops
from pydantic_ai_harness.prompt_injection_defender import PromptInjectionDefender
from pydantic_ai_harness.conversation_search import ConversationSearch,SnapshotHistorySource
from pydantic_ai_harness.compaction import ClampOversizedMessages,SummarizingCompaction
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

log=logging.getLogger(__name__)

def _on_injection(ctx,call,verdict):
    log.warning("injection blocked in %s (risk=%s)", call.tool_name, verdict.risk_level)

def _memory_caps(store):
    return [
        StepPersistence(store,agent_name="friend"),
        ConversationSearch(SnapshotHistorySource(store),scope="all"),
        ClampOversizedMessages(max_part_chars=8000),
        SummarizingCompaction(max_messages=30,keep_messages=12)
    ]

def _tool_caps(pool):
    return [
        ToolOutputLimits(
                    bands=[
                        Band(over=100_000,action=Spill(then=Truncate())),
                        Band(over=20_000,action=Summarize(then=Truncate())),
                        Band(over=5000,action=Truncate(max_chars=5_000))
                        ],
                        store=PostgresSpillStore(pool)
                    ),
    ]

def _safety_caps(pool):
    return [
        PromptInjectionDefender(block_high_risk=True,on_detection=_on_injection),
        RepairToolArguments(),
        DetectLoops(repeated_call_threshold=3),
                SpendLimits(
                    budgets=[
                        Budget(usd=Decimal("1.00"),window="run",name="per_message"),
                        Budget(usd=Decimal("2.00"),window="day",tokens=900_000,warn_at=0.8),
        
                    ],
                    store  = PostgresSpendStore(pool,table="friend_spend"),
            ),
    ]



def build_capabilities(store,pool):
    return [*_memory_caps(store),*_safety_caps(pool),*_tool_caps(pool),]