from pydantic_ai_harness.step_persistence import InMemoryStepStore
from app.harness.capabilities import build_capabilities

caps = build_capabilities(InMemoryStepStore(), object())
print(len(caps), [type(c).__name__ for c in caps])