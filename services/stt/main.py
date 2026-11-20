"""Vosk STT service: POST /transcribe, WebSocket /ws, GET /health."""
import os

# One thread only: Kaldi is effectively single-threaded and we have ~0.1 vCPU.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import asyncio
import hmac
import io
import json
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)

RATE = 16000
MAX_SECONDS = 30
MAX_PCM_BYTES = RATE * 2 * MAX_SECONDS            # 960000
MAX_BODY_BYTES = MAX_PCM_BYTES + 4096             # + WAV header slack
CHUNK = 8000                                      # 0.25 s of PCM16
MODELS = {
    "hi": "vosk-model-small-hi-0.22",
    "en": "vosk-model-small-en-in-0.4",
}
MODEL_DIR = Path(os.environ.get("STT_MODEL_DIR", Path(__file__).parent / "models"))
RAW_TYPES = {"", "application/octet-stream", "audio/pcm", "audio/l16", "audio/raw",
             "audio/x-raw"}
# Magic bytes of common non-PCM containers we refuse to decode.
FOREIGN_MAGIC = (b"ID3", b"OggS", b"fLaC", b"\x1aE\xdf\xa3", b"\xff\xfb", b"\xff\xf3",
                 b"\xff\xf1", b"\xff\xf9", b"FORM")

state: dict = {"model": None, "models": {}, "lang": None, "ready": False}
infer_lock = asyncio.Lock()   # one decode at a time on 0.1 vCPU


def rss_mb() -> float | None:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def peak_mb() -> float | None:
    try:
        import resource  # Linux only
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        return None


def log_mem(tag: str) -> None:
    print(f"stt mem {tag} lang={state['lang']} rss_mb={rss_mb()} peak_mb={peak_mb()}",
          flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("STT_KEY"):
        raise RuntimeError("STT_KEY environment variable is required")
    lang = os.environ.get("STT_LANG", "hi").lower()
    # "both" loads every model (memory experiment); normal use is hi or en.
    langs = list(MODELS) if lang == "both" else [lang]
    if any(x not in MODELS for x in langs):
        raise RuntimeError("STT_LANG must be 'hi', 'en' or 'both'")
    t0 = time.perf_counter()
    models = {}
    for x in langs:
        path = MODEL_DIR / MODELS[x]
        if not path.is_dir():
            raise RuntimeError(f"model directory missing: {path}")
        models[x] = Model(str(path))
        rec = KaldiRecognizer(models[x], RATE)
        rec.SetWords(False)
        rec.AcceptWaveform(b"\x00\x00" * RATE)   # warm-up: 1 s of silence
        rec.FinalResult()
    state.update(model=models[langs[0]], models=models, lang=lang, ready=True,
                 load_ms=round((time.perf_counter() - t0) * 1000))
    log_mem(f"ready load_ms={state['load_ms']}")
    yield
    state.update(model=None, ready=False)


app = FastAPI(title="stt", lifespan=lifespan)


def key_ok(supplied: str) -> bool:
    expected = os.environ.get("STT_KEY", "")
    return bool(expected) and hmac.compare_digest(supplied.encode(), expected.encode())


def new_recognizer(words: bool = False, lang: str | None = None) -> KaldiRecognizer:
    rec = KaldiRecognizer(state["models"].get(lang or "", state["model"]), RATE)
    rec.SetWords(words)
    return rec


def decode(pcm: bytes, words: bool, lang: str | None = None) -> str:
    rec = new_recognizer(words, lang)
    for i in range(0, len(pcm), CHUNK):
        rec.AcceptWaveform(pcm[i:i + CHUNK])
    return json.loads(rec.FinalResult()).get("text", "")


def extract_pcm(body: bytes, content_type: str) -> bytes:
    ctype = content_type.split(";")[0].strip().lower()
    if body[:4] == b"RIFF":
        try:
            with wave.open(io.BytesIO(body)) as w:
                if (w.getcomptype() != "NONE" or w.getnchannels() != 1
                        or w.getsampwidth() != 2 or w.getframerate() != RATE):
                    raise ValueError
                if w.getnframes() > RATE * MAX_SECONDS:
                    raise HTTPException(413, f"audio longer than {MAX_SECONDS}s")
                return w.readframes(w.getnframes())
        except (wave.Error, ValueError, EOFError):
            raise HTTPException(415, "WAV must be mono PCM16 at 16000 Hz") from None
    if (ctype not in RAW_TYPES or body[:4] in FOREIGN_MAGIC or body[:3] in FOREIGN_MAGIC
            or body[4:8] == b"ftyp"):
        raise HTTPException(415, "unsupported audio: send mono PCM16 16 kHz raw bytes or WAV")
    if len(body) % 2:
        raise HTTPException(400, "raw PCM16 must have an even number of bytes")
    return body


@app.get("/health")
async def health():
    if not state["ready"]:
        return JSONResponse({"ok": False}, status_code=503)
    return {"ok": True}


@app.post("/transcribe")
async def transcribe(request: Request, x_stt_key: str = Header(default=""),
                     words: bool = False, lang: str | None = None):
    if not key_ok(x_stt_key):
        raise HTTPException(401, "invalid or missing X-STT-Key")
    if not state["ready"]:
        raise HTTPException(503, "model not loaded")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(413, "request body too large")
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > MAX_BODY_BYTES:
            raise HTTPException(413, "request body too large")
    pcm = extract_pcm(bytes(buf), request.headers.get("content-type", ""))
    if len(pcm) > MAX_PCM_BYTES:
        raise HTTPException(413, f"audio longer than {MAX_SECONDS}s")
    t0 = time.perf_counter()
    async with infer_lock:
        text = await run_in_threadpool(decode, pcm, words, lang)
    log_mem(f"transcribe bytes={len(pcm)}")
    return {"text": text, "ms": round((time.perf_counter() - t0) * 1000)}


@app.websocket("/ws")
async def ws(sock: WebSocket):
    """Binary frames = PCM16 16 kHz mono. Text 'end' (or {"eof":1}) = finish.
    Auth: ?key=... query param, or first text message {"key": "..."}."""
    await sock.accept()
    supplied = sock.query_params.get("key", "")
    if not supplied:
        try:
            first = await asyncio.wait_for(sock.receive(), timeout=10)
        except (TimeoutError, WebSocketDisconnect):
            await sock.close(code=1008)
            return
        if first.get("type") == "websocket.disconnect":
            return
        if first.get("text"):
            try:
                supplied = str(json.loads(first["text"]).get("key", ""))
            except (ValueError, AttributeError):
                supplied = first["text"]
    if not key_ok(supplied) or not state["ready"]:
        await sock.close(code=1008)
        return
    rec = new_recognizer(False, sock.query_params.get("lang"))
    parts: list[str] = []
    total = 0
    last_partial = ""
    t0 = time.perf_counter()
    try:
        while True:
            msg = await sock.receive()
            if msg["type"] == "websocket.disconnect":
                return
            if msg.get("bytes"):
                data = msg["bytes"]
                total += len(data)
                if total > MAX_PCM_BYTES:
                    await sock.close(code=1009, reason="stream longer than 30s")
                    return
                async with infer_lock:
                    done = await run_in_threadpool(rec.AcceptWaveform, data)
                    res = rec.Result() if done else rec.PartialResult()
                obj = json.loads(res)
                if done:
                    if obj.get("text"):
                        parts.append(obj["text"])
                    last_partial = ""
                    if parts:
                        await sock.send_json({"type": "partial", "text": " ".join(parts)})
                else:
                    p = obj.get("partial", "")
                    if p and p != last_partial:
                        last_partial = p
                        await sock.send_json({"type": "partial",
                                              "text": " ".join(parts + [p])})
            elif msg.get("text") is not None:
                t = msg["text"].strip().lower()
                if t in ("end", "eof") or '"eof"' in t:
                    async with infer_lock:
                        fin = json.loads(rec.FinalResult()).get("text", "")
                    if fin:
                        parts.append(fin)
                    await sock.send_json({"type": "final", "text": " ".join(parts),
                                          "ms": round((time.perf_counter() - t0) * 1000)})
                    await sock.close()
                    return
    except WebSocketDisconnect:
        return
