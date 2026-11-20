"""Piper TTS service: Hindi (Rohan, medium) on a Nano replica (~0.1 vCPU, 500 MiB)."""
import os

# One thread everywhere: on a 0.1 vCPU box default thread pools fight each other.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import gc
import hashlib
import hmac
import io
import json
import sys
import threading
import time
import wave
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

import onnxruntime as ort
from chunker import chunk_text
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from piper import PiperVoice
from piper.config import PiperConfig, SynthesisConfig
from pydantic import BaseModel
from translit import to_devanagari

TTS_KEY = os.environ["TTS_KEY"]  # KeyError at startup if missing
if not TTS_KEY:
    raise RuntimeError("TTS_KEY is empty")

VOICE_NAME = "hi_IN-rohan-medium"
VOICE_DIR = Path(__file__).parent / "voices"
MAX_CHARS = 600
CACHE_MAX_BYTES = 24 * 1024 * 1024  # PCM cache cap (keeps peak RSS well under 400 MB)

STOCK = {
    "ek-minute": "एक मिनट",
    "haan-bolo": "हाँ बोलो",
    "samajh-nahi-aaya": "मुझे समझ नहीं आया",
    "dobara-bolo": "कृपया दोबारा बोलिए",
    "dhanyavaad": "धन्यवाद",
    "namaste": "नमस्ते",
}

try:  # glibc: serve big tensors via mmap so they go back to the OS right after each piece
    import ctypes

    _libc = ctypes.CDLL("libc.so.6")
    _libc.mallopt(-3, 128 * 1024)  # M_MMAP_THRESHOLD
except Exception:
    _libc = None


def trim_memory():
    gc.collect()
    if _libc is not None:
        try:
            _libc.malloc_trim(0)
        except Exception:
            pass


state: dict = {}
synth_lock = threading.Lock()  # one synthesis at a time: bounds memory on the Nano
stats: dict = {"last": None}
syn_cfg = SynthesisConfig()


class PcmCache:
    """LRU cache of PCM16 bytes keyed by sha256(voice, text), capped by total bytes."""

    def __init__(self, cap: int):
        self.cap, self.size, self.d = cap, 0, OrderedDict()
        self.hits = self.misses = 0
        self._lock = threading.Lock()

    @staticmethod
    def key(voice: str, text: str) -> str:
        return hashlib.sha256(f"{voice}\0{text}".encode()).hexdigest()

    def get(self, k: str):
        with self._lock:
            v = self.d.get(k)
            if v is None:
                self.misses += 1
                return None
            self.d.move_to_end(k)
            self.hits += 1
            return v

    def put(self, k: str, v: bytes):
        with self._lock:
            if k in self.d or len(v) > self.cap:
                return
            self.d[k] = v
            self.size += len(v)
            while self.size > self.cap:
                _, old = self.d.popitem(last=False)
                self.size -= len(old)


cache = PcmCache(CACHE_MAX_BYTES)


MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/"
    "hi_IN-rohan-medium.onnx"
)


def ensure_model() -> tuple[Path, Path]:
    """Use the bundled model + config if present; otherwise download once into a temp dir."""
    bundled = VOICE_DIR / f"{VOICE_NAME}.model"
    bundled_cfg = VOICE_DIR / f"{VOICE_NAME}.json"
    if bundled.exists() and bundled_cfg.exists():
        state["model_source"] = "bundled"
        return bundled, bundled_cfg
    import tempfile
    import urllib.request

    tmpdir = Path(tempfile.gettempdir())
    dest = tmpdir / f"{VOICE_NAME}.model"
    dest_cfg = tmpdir / f"{VOICE_NAME}.json"
    t0 = time.perf_counter()
    for path, url in ((dest, MODEL_URL), (dest_cfg, MODEL_URL + ".json")):
        if not path.exists():
            part = path.with_suffix(path.suffix + ".part")
            urllib.request.urlretrieve(url, part)
            part.replace(path)
            state["download_s"] = time.perf_counter() - t0
    state["model_source"] = "downloaded"
    return dest, dest_cfg


def load_voice() -> PiperVoice:
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    so.enable_cpu_mem_arena = False  # return memory to the OS between pieces
    so.enable_mem_pattern = False
    model, cfg_path = ensure_model()
    cfg = PiperConfig.from_dict(json.loads(cfg_path.read_text("utf-8")))
    sess = ort.InferenceSession(str(model), sess_options=so, providers=["CPUExecutionProvider"])
    return PiperVoice(session=sess, config=cfg)


def synth_piece(piece: str) -> bytes:
    """Synthesize one piece to PCM16 bytes (cached). Frees memory afterwards."""
    k = PcmCache.key(VOICE_NAME, piece)
    hit = cache.get(k)
    if hit is not None:
        return hit
    voice: PiperVoice = state["voice"]
    with synth_lock:
        t0 = time.perf_counter()
        pcm = b"".join(c.audio_int16_bytes for c in voice.synthesize(piece, syn_cfg))
        dt = time.perf_counter() - t0
        audio_s = len(pcm) / 2 / state["rate"]
        stats["last"] = {"wall_s": dt, "audio_s": audio_s}
        trim_memory()
    cache.put(k, pcm)
    return pcm


def prepare(text: str, translit: bool) -> list[str]:
    if translit:
        text = to_devanagari(text)
    return chunk_text(text)


def wav_bytes(pcm: bytes, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def rss_mb() -> tuple[float | None, float | None]:
    try:
        cur = peak = None
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                cur = int(line.split()[1]) / 1024
            elif line.startswith("VmHWM:"):
                peak = int(line.split()[1]) / 1024
        return cur, peak
    except OSError:
        return None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    voice = load_voice()
    state["voice"] = voice
    state["rate"] = voice.config.sample_rate
    t1 = time.perf_counter()
    synth_piece("नमस्ते")  # warm-up: first inference is slow (kernels, espeak init)
    state["load_s"], state["warmup_s"] = t1 - t0, time.perf_counter() - t1
    state["ready"] = True
    yield
    state.clear()


app = FastAPI(title="tts", lifespan=lifespan)


def check_key(x_tts_key: str):
    if not x_tts_key or not hmac.compare_digest(x_tts_key.encode(), TTS_KEY.encode()):
        raise HTTPException(status_code=401, detail="bad key")


class SpeakRequest(BaseModel):
    text: str
    translit: bool = False  # Roman Hinglish -> Devanagari before synthesis


def validated_pieces(req: SpeakRequest) -> list[str]:
    if len(req.text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail=f"text longer than {MAX_CHARS} chars")
    pieces = prepare(req.text, req.translit)
    if not pieces:
        raise HTTPException(status_code=422, detail="empty text")
    return pieces


@app.get("/health")
def health():
    return {"ok": bool(state.get("ready"))}


@app.post("/speak")
def speak(req: SpeakRequest, x_tts_key: str = Header(default="")):
    check_key(x_tts_key)
    pieces = validated_pieces(req)
    t0 = time.perf_counter()
    pcm = b"".join(synth_piece(p) for p in pieces)
    wall = time.perf_counter() - t0
    rate = state["rate"]
    audio_s = len(pcm) / 2 / rate
    return Response(
        wav_bytes(pcm, rate),
        media_type="audio/wav",
        headers={
            "X-Sample-Rate": str(rate),
            "X-Pieces": str(len(pieces)),
            "X-RTF": f"{wall / audio_s:.3f}" if audio_s else "0",
        },
    )


@app.post("/speak/stream")
def speak_stream(req: SpeakRequest, x_tts_key: str = Header(default="")):
    check_key(x_tts_key)
    pieces = validated_pieces(req)

    def gen():
        for p in pieces:
            yield synth_piece(p)  # first bytes leave after the first piece only

    return StreamingResponse(
        gen(),
        media_type="application/octet-stream",
        headers={
            "X-Sample-Rate": str(state["rate"]),
            "X-Sample-Format": "s16le",
            "X-Channels": "1",
            "X-Pieces": str(len(pieces)),
        },
    )


@app.get("/stock/{name}")
def stock(name: str, x_tts_key: str = Header(default="")):
    check_key(x_tts_key)
    text = STOCK.get(name)
    if text is None:
        raise HTTPException(status_code=404, detail=f"unknown phrase; have: {sorted(STOCK)}")
    pcm = synth_piece(text)  # first use renders, later uses are cache hits
    return Response(wav_bytes(pcm, state["rate"]), media_type="audio/wav")


@app.get("/stats")
def get_stats(x_tts_key: str = Header(default="")):
    check_key(x_tts_key)
    cur, peak = rss_mb()
    return {
        "rss_mb": cur,
        "peak_rss_mb": peak,
        "last_synth": stats["last"],
        "cache": {"bytes": cache.size, "entries": len(cache.d), "hits": cache.hits, "misses": cache.misses},
        "python": sys.version.split()[0],
        "model_source": state.get("model_source"),
        "download_s": state.get("download_s"),
        "load_s": state.get("load_s"),
        "warmup_s": state.get("warmup_s"),
    }


@app.post("/stats/reset-peak")
def reset_peak(x_tts_key: str = Header(default="")):
    check_key(x_tts_key)
    try:
        Path("/proc/self/clear_refs").write_text("5")
        return {"reset": True}
    except OSError:
        return {"reset": False}
