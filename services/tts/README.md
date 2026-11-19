# tts

Piper TTS service (Hindi, Rohan medium) for FastAPI Cloud / Vercel.

The voice model is not in git (63 MB). Download it before running or deploying:

```
cd services/tts
curl -L -o voices/hi_IN-rohan-medium.model https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx
```

The config `voices/hi_IN-rohan-medium.json` is in git. The model is saved with a `.model`
extension so `*.onnx` ignore rules do not drop it from a deploy upload.

Run: `TTS_KEY=... uv run uvicorn main:app`. Requests need the `X-TTS-Key` header (except `/health`).
