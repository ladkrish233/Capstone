// Circuit: hold the button, talk, let go. Sends a 16 kHz mono WAV to /voice and plays the reply.
// Same origin as the api, so no CORS. The API key lives only in this phone's localStorage.

const $ = (id) => document.getElementById(id);
const talk = $("talk");
const statusEl = $("status");
const timingEl = $("timing");
const replayBtn = $("replay");
const keyPanel = $("key-panel");
const keyForm = $("key-form");
const keyInput = $("key-input");

const MAX_MS = 12000;          // auto-stop. stt time grows with length, keep turns short
const MIN_MS = 600;            // shorter than this is an accidental tap
const WARM_EVERY_MS = 4 * 60 * 1000;
const KEY_NAME = "circuit_key";

const SAY = {
  idle: "Dabao aur bolo",
  wake: "Line mila raha hoon…",
  listen: "Sun raha hoon…",
  think: "Soch raha hoon…",
  speak: "Bol raha hoon…",
};

// ---------- tiny helpers ----------
let memoryKey = "";
function loadKey() {
  try { return localStorage.getItem(KEY_NAME) || ""; } catch { return memoryKey; }
}
function saveKey(v) {
  memoryKey = v;
  try { localStorage.setItem(KEY_NAME, v); } catch { /* private mode: keep in memory */ }
}
function forgetKey() {
  memoryKey = "";
  try { localStorage.removeItem(KEY_NAME); } catch { /* ignore */ }
}

let key = loadKey();

function setStatus(text, state = "idle") {
  statusEl.textContent = text;
  statusEl.dataset.state = state;
}

function showKeyPanel() {
  keyPanel.hidden = false;
  keyInput.value = "";
  keyInput.focus();
}

function badKey() {
  forgetKey();
  key = "";
  setStatus("Key galat hai. Dobara daalo.", "error");
  showKeyPanel();
}

// ---------- warm-up: wake embed, stt, tts and the database ----------
let lastWarm = 0;
async function warm({ quiet = false, retried = false } = {}) {
  if (!key) return;
  if (quiet && Date.now() - lastWarm < WARM_EVERY_MS) return;
  if (!quiet) setStatus(SAY.wake, "wake");
  try {
    const r = await fetch("/warmup", { headers: { "X-Api-Key": key } });
    if (r.status === 401) return badKey();
    if (!r.ok) throw new Error("warmup " + r.status);
    const j = await r.json();
    const asleep = ["embed", "stt", "tts", "db"].filter((k) => j[k] === false);
    lastWarm = Date.now();
    if (asleep.length && !retried) {
      // A service that was cold can answer a moment later. Try once more.
      if (!quiet) setStatus("Thodi der… jaag rahe hain", "wake");
      setTimeout(() => warm({ quiet, retried: true }), 2500);
      return;
    }
    if (!quiet) {
      if (asleep.length) setStatus("Ye so rahe hain: " + asleep.join(", "), "error");
      else setStatus(SAY.idle, "idle");
    }
  } catch {
    if (!quiet) setStatus("Net check karo", "error");
  }
}

// ---------- recording ----------
let stream = null;
let recorder = null;
let chunks = [];
let recording = false;   // true from press until the recorder has stopped
let wantStop = false;    // released before the mic finished opening
let startedAt = 0;
let timer = 0;
let busy = false;

function stopTracks() {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null;
}

async function press() {
  if (busy || recording) return;
  if (!key) return showKeyPanel();
  recording = true;
  wantStop = false;
  replayBtn.classList.add("ghost");
  timingEl.textContent = "";
  warm({ quiet: true });

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch {
    recording = false;
    return setStatus("Mic ki permission do", "error");
  }

  if (wantStop) {                       // finger came up while the permission prompt was open
    stopTracks();
    recording = false;
    return setStatus("Thoda der dabake rakho", "idle");
  }

  chunks = [];
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = finish;
  startedAt = performance.now();
  recorder.start();
  talk.classList.add("live");
  setStatus(SAY.listen, "listen");
  timer = setTimeout(release, MAX_MS);
  if (navigator.vibrate) navigator.vibrate(15);
}

function release() {
  if (!recording) return;
  wantStop = true;
  clearTimeout(timer);
  if (recorder && recorder.state === "recording") recorder.stop();
}

// ---------- audio -> 16 kHz mono 16-bit WAV (what the stt service expects) ----------
async function toWav16k(blob) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  let decoded;
  try {
    decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  } finally {
    ctx.close();
  }
  const frames = Math.max(1, Math.ceil(decoded.duration * 16000));
  const off = new OfflineAudioContext(1, frames, 16000);   // resamples and mixes down to mono
  const src = off.createBufferSource();
  src.buffer = decoded;
  src.connect(off.destination);
  src.start();
  const out = (await off.startRendering()).getChannelData(0);

  let peak = 0;
  for (let i = 0; i < out.length; i++) peak = Math.max(peak, Math.abs(out[i]));
  if (peak > 0 && peak < 0.35) {                           // quiet phone mic: lift it, gently
    const gain = Math.min(0.6 / peak, 4);
    for (let i = 0; i < out.length; i++) out[i] *= gain;
  }
  return { wav: encodeWav(out, 16000), peak };
}

function encodeWav(samples, rate) {
  const n = samples.length;
  const buf = new ArrayBuffer(44 + n * 2);
  const v = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF");  v.setUint32(4, 36 + n * 2, true);
  str(8, "WAVE");  str(12, "fmt ");
  v.setUint32(16, 16, true);  v.setUint16(20, 1, true);  v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);   v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buf;
}

// ---------- send, then play ----------
const player = new Audio();
let lastUrl = "";

async function finish() {
  talk.classList.remove("live");
  stopTracks();
  recording = false;
  const heldMs = performance.now() - startedAt;
  if (heldMs < MIN_MS) return setStatus("Thoda der dabake rakho", "idle");

  busy = true;
  document.body.dataset.busy = "true";
  talk.disabled = true;
  try {
    setStatus(SAY.think, "think");
    const { wav, peak } = await toWav16k(new Blob(chunks, { type: recorder.mimeType }));
    if (peak < 0.02) return setStatus("Awaaz nahi aayi. Paas se bolo.", "error");

    const r = await fetch("/voice", { method: "POST", headers: { "X-Api-Key": key }, body: wav });
    if (r.status === 401) return badKey();
    if (r.status === 422) return setStatus("Kuch sunai nahi diya. Phir se bolo.", "error");
    if (r.status === 413) return setStatus("Bahut lamba. Chhota bolo.", "error");
    if (!r.ok) {
      let why = "";
      try { why = (await r.json()).detail || ""; } catch { /* not json */ }
      return setStatus(`Dikkat (${r.status}) ${why}`.trim(), "error");
    }

    const h = r.headers;
    if (h.get("x-time-stt")) {
      timingEl.textContent =
        `stt ${h.get("x-time-stt")}s · agent ${h.get("x-time-agent")}s · tts ${h.get("x-time-tts")}s`;
    }
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(await r.blob());
    await speak();
  } catch (e) {
    setStatus("Kuch gadbad: " + (e && e.message ? e.message : "unknown"), "error");
  } finally {
    busy = false;
    document.body.dataset.busy = "false";
    talk.disabled = false;
  }
}

async function speak() {
  player.src = lastUrl;
  setStatus(SAY.speak, "speak");
  replayBtn.classList.remove("ghost");
  try {
    await player.play();
  } catch {
    setStatus("Jawab ready hai. Neeche dabao.", "idle");   // the browser blocked autoplay
  }
}

player.addEventListener("ended", () => setStatus(SAY.idle, "idle"));
replayBtn.addEventListener("click", () => { if (lastUrl) { player.currentTime = 0; speak(); } });

// ---------- wiring ----------
talk.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  try { talk.setPointerCapture(e.pointerId); } catch { /* ignore */ }
  press();
});
talk.addEventListener("pointerup", release);
talk.addEventListener("pointercancel", release);
talk.addEventListener("contextmenu", (e) => e.preventDefault());
talk.addEventListener("keydown", (e) => {
  if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); press(); }
});
talk.addEventListener("keyup", (e) => {
  if (e.key === " " || e.key === "Enter") release();
});

keyForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const v = keyInput.value.trim();
  if (!v) return;
  saveKey(v);
  key = v;
  keyInput.value = "";
  keyPanel.hidden = true;
  warm();
});
$("change-key").addEventListener("click", showKeyPanel);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") warm({ quiet: true });
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => { /* optional */ });
  });
}

if (key) warm();
else showKeyPanel();
