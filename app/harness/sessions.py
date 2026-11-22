from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic_ai_harness.step_persistence import continue_run

TZ=ZoneInfo("Asia/Kolkata")

def today_id()->str:
    return datetime.now(TZ).date().isoformat()

async def load_history(store,conversation_id):
    runs=await store.list_runs(conversation_id=conversation_id)
    for r in reversed(runs):
        try:
            return await continue_run(store,run_id=r.run_id)
        except LookupError:
            continue
    return []