import os
import time
import asyncio
import httpx
import logging
from fastapi import APIRouter,Header,HTTPException
from app.security import check_key
from app.db import get_db_health

logger=logging.getLogger(__name__)
router=APIRouter()

EMBED = os.environ["EMBED_URL"].rstrip("/").removesuffix("/embed")
STT = os.environ["STT_URL"].rstrip("/")
TTS = os.environ["TTS_URL"].rstrip("/")

async def ping(client,name,url):
    try:  
        r = await client.get(url)
        r.raise_for_status()
        return (name,True)
    except Exception:
        logger.warning("warmup ping failed: %s", name)
        return (name,False)

async def ping_db():
    try:
        await asyncio.to_thread(get_db_health)
        return ("db",True)
    except :
        logger.exception("warmup db failed")
        return("db",False)

@router.get("/warmup")
async def warmup(x_api_key:str|None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    t0 = time.perf_counter()    
    async with httpx.AsyncClient(timeout=30) as client:
        results=await asyncio.gather(
            ping(client,"embed",f"{EMBED}/health"),
            ping(client,"stt",f"{STT}/health"),
            ping(client,"tts",f"{TTS}/health"),
            ping_db()
        )
    return {**dict(results), "seconds": round(time.perf_counter() - t0, 1)}






@router.get("/health/db")
def db_health(x_health_key: str | None = Header(default=None)):
    check_key(x_health_key,"HEALTH_KEY")
    try:
        return get_db_health()
    except Exception:
        logger.exception("db health check failed")
        raise HTTPException(status_code=503,detail="db unavailable")