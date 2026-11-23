import array
import io
import os
import wave

import httpx
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

SECONDS = 10
RATE = 16000

print(f"Speak now for {SECONDS} seconds...")
with sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16") as stream:
    pcm, _ = stream.read(RATE * SECONDS)
pcm = bytes(pcm)
print("Recorded. Sending...")

buf = io.BytesIO()
with wave.open(buf, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
    w.writeframes(pcm)

with open("sent.wav", "wb") as f:
    f.write(buf.getvalue())
print("peak level:", max(abs(x) for x in array.array("h", pcm)))

url = os.environ.get("API_URL", "http://localhost:8000") + "/voice"
r = httpx.post(url, content=buf.getvalue(),
               headers={"X-Api-Key": os.environ["API_KEY"]}, timeout=90)
print(r.status_code, {k: v for k, v in r.headers.items() if k.startswith("x-time")})
if r.status_code == 200:
    with open("reply.wav", "wb") as f:
        f.write(r.content)
    print("saved reply.wav, playing...")
    os.startfile("reply.wav")
else:
    print(r.text)