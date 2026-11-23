from pydantic_ai_harness.step_persistence import StepPersistence
from pydantic_ai_harness.tool_output_limits import Band,ToolOutputLimits,Truncate

def build_capabilities(store):
    return [
        StepPersistence(store,agent_name="friend"),
        ToolOutputLimits(bands=[Band(over=4000,action=Truncate)])
    ]