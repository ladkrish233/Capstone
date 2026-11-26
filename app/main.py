import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import tracker
from app.api.chat import router as chat_router
from app.api.reminders import router as reminder_router
from app.api.voice import router as voice_router
from app.api.warmup import router as warmup_router
from app.harness.brain import Brain
from app.harness.telementry import setup_telementry
from app.pool import make_pool

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app:FastAPI):
    setup_telementry()  # before Brain so agents are instrumented
    app.state.pool=await make_pool()
    tracker.set_pool(app.state.pool)
    app.state.brain=Brain(app.state.pool)
    yield
    tracker.set_pool(None)
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)

app.include_router(warmup_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(reminder_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Must be last: a mount at "/" matches every path registered after it.
app.mount("/",StaticFiles(directory="static",html=True),name="static")
