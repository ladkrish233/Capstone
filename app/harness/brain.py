import asyncio

from pydantic_ai_harness.step_persistence import PostgresStepStore
from pydantic_ai import UsageLimits

from app.agent import build_agent
from app.harness.capabilities import build_capabilities
from app.harness.config import MODEL
from app.harness.sessions import load_history, today_id

LIMITS=UsageLimits(request_limit=10,tool_calls_limit=8)


class Brain:
    def __init__(self,pool):
        self.store=PostgresStepStore(pool,table="friends_steps")
        self.caps=build_capabilities(self.store,pool)
        self.agent=build_agent(MODEL,self.caps)
        self._lock=asyncio.Lock()
    
    async def ask(self,message:str):
        async with self._lock:
            conv = today_id()
            history = await load_history(self.store,conv)
            return await self.agent.run(
                message,
                message_history=history,
                conversation_id=conv,
                usage_limits=LIMITS
            )

