import io
import logging
import os
import time
import wave

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic_ai.exceptions import UsageLimitExceeded

from app.security import check_key

log=logging.getLogger(__name__)
router=APIRouter()
load_dotenv()

STT, TTS = os.environ["STT_URL"].rstrip("/"), os.environ["TTS_URL"].rstrip("/")
STT_KEY, TTS_KEY = os.environ["STT_KEY"], os.environ["TTS_KEY"]
RATE = int(os.environ.get("TTS_RATE", "22050"))

MAX_TTS = 600

def fit(text: str) -> str:
    text = text.strip()
    if not text:
        return "Maaf kijiye, mere paas kehne ke liye kuch nahi hai."
    if len(text) <= MAX_TTS:
        return text
    cut = text[:MAX_TTS]
    end = max(cut.rfind(c) for c in ".?!।")
    return cut[:end + 1] if end > 0 else cut

async def call(c, name, url, **kw):
    try:
        r = await c.post(url, **kw)
        r.raise_for_status()
        return r
    except httpx.HTTPStatusError as e:
        log.error("%s returned %s from %s: %s", name, e.response.status_code, url, e.response.text[:200])
        raise HTTPException(status_code=502, detail=f"{name} unavailable")
    except Exception:
        log.exception("%s failed (%s)", name, url)
        raise HTTPException(status_code=502, detail=f"{name} unavailable")

@router.post("/voice")
async def voice(request:Request,x_api_key:str|None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    body = await request.body()
    if not body or len(body)>  2_000_000:
        raise HTTPException(413,"audio missing or too long")
    with wave.open(io.BytesIO(body)) as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, 16000):
            raise HTTPException(422, "send WAV: mono, 16-bit, 16000 Hz")
        pcm=w.readframes(w.getnframes())

    t0=time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as c :
        r = await call(c, "stt", f"{STT}/transcribe", content=pcm, headers={"X-STT-Key": STT_KEY})
        text=r.json()["text"].strip()
        t1=time.perf_counter()
        if not text:
            raise HTTPException(422, "did not hear anything")
        try:
            answer = (await request.app.state.brain.ask(text)).output
        except UsageLimitExceeded:
            answer= "I've reached my limit for now. Let's talk again a bit later."
        except Exception:
            log.exception("agent failed")
            raise HTTPException(502, "agent unavailable")
        t2=time.perf_counter()

        r = await call(c, "tts", f"{TTS}/speak/stream", json={"text": fit(answer)}, headers={"X-TTS-Key": TTS_KEY})
        t3=time.perf_counter()

        buf=io.BytesIO()
        with wave.open(buf,"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
            w.writeframes(r.content)
        log.info("voice stt=%.1fs agent=%.1fs tts=%.1fs", t1 - t0, t2 - t1, t3 - t2)
        return Response(buf.getvalue(),media_type="audio/wav", headers={
        "X-Time-STT": f"{t1 - t0:.1f}", "X-Time-Agent": f"{t2 - t1:.1f}", "X-Time-TTS": f"{t3 - t2:.1f}"})

        