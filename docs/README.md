# stt-bench: Hindi / Hinglish speech-to-text comparison

Small benchmark to pick a light, free, local STT model for the "Friend" voice assistant.

**Decision: Vosk small Hindi (`vosk-model-small-hi-0.22`).**
Collabora tiny-hindi is the fallback. whisper-tiny-hinglish was rejected.

## Results

Test set: 12 short clips in `clips/` (`NN.wav` with its reference text in `NN.txt`), 141 s of audio in total. CPU only.

### Raw Devanagari WER (first run)

| Model | Decode time | Real-time factor | Peak RAM | WER |
|---|---|---|---|---|
| collabora tiny-hindi (faster-whisper, int8) | 10.3 s | 0.073 | 322 MB | 12.6% |
| Vosk small Hindi | 14.1 s | 0.100 | 269 MB | 13.6% |
| whisper-tiny-hinglish | 3.0 s | 0.021 | 306 MB | 107% (not meaningful) |

whisper-tiny-hinglish writes Roman letters but the references are Devanagari, so this WER is not a fair score.

### Fair comparison (`score_roman.py`)

Every output is mapped to a consonant skeleton (drops vowels, collapses spelling variants such as aspirates, retroflexes, v/w, sh/s, m/n), so Roman and Devanagari output can be compared. A control run (each reference scored against another clip's text) gives 112% WER, so the metric is strict.

| Model | Real-time factor | Peak RAM | Skeleton WER | Skeleton CER |
|---|---|---|---|---|
| collabora tiny-hindi | 0.061 | 322 MB | 12.5% | 4.1% |
| Vosk small Hindi | 0.099 | 284 MB | 13.2% | 6.2% |
| whisper-tiny-hinglish | 0.022 | 306 MB | 42.0% | 15.8% |

Not run: IndicConformer Hindi GGUF (needs a parakeet.cpp build; claimed about 13.5% WER).

## Why Vosk

- Lowest RAM (about 284 MB), so it fits a small host next to the API.
- Streaming, so text can appear while the user is still speaking.
- Accuracy is within about 1 point of collabora on WER (CER is worse: 6.2% vs 4.1%).
- Collabora is the fallback if Vosk quality is not enough in real use. It is more accurate but not streaming.
- whisper-tiny-hinglish is fast but far less accurate (42% WER).

## Deployment test: FastAPI Cloud (Nano)

A tiny app (`stt-vosk-test`: loads Vosk once, one `/transcribe` endpoint) was deployed on FastAPI Cloud Nano (limit 0.1 vCPU, 500 MB, us-east-1) and tested with 5, 10 and 15 s clips, two runs each after a warm-up call.

| Clip | Run 1 | Run 2 | Local, same code |
|---|---|---|---|
| 5 s | 2.89 s | 2.19 s | 0.83 s |
| 10 s | 3.18 s | 3.83 s | 1.13 s |
| 15 s | 4.55 s | 4.39 s | 1.73 s |

- Times are total request times from the client (upload and network included). A bare `/docs` request took about 0.36 s.
- The cloud machine is about 3x slower than local for the same work (0.1 vCPU).
- Each extra second of audio adds about 0.2 s of processing (about 5x faster than real time), plus a fixed overhead of about 1.5 s per request.
- The transcript matched the local run, so the deploy is correct.
- **Memory:** peak about 305 MB (61% of 500 MB) in the dashboard. Local idle was 233 MB and peak 317 MB. The dashboard chart had a single data point, so treat 305 MB as a minimum and recheck after a longer session.
- The CPU chart showed 36% average per replica. It is an average over a time window, so real use during each request was higher (probably at the 0.1 vCPU limit).
- Only two runs per clip, so differences under about 0.7 s are noise.

**Conclusion:** Vosk small Hindi fits FastAPI Cloud Nano. Upload mode is acceptable (5 s clip about 2 to 3 s) but not snappy. Next step is WebSocket streaming: Vosk is a streaming model and runs faster than real time, so transcription happens while the user is still talking and the final text is ready well under a second after they stop. Groq whisper-large-v3-turbo is the fallback if the Nano is too slow in real use.

The test app was deleted after the test.

## Notes and warnings

- **Memory growth on long audio.** On a 24-minute file Vosk grew from 179 MB to 519 MB (that file was Bengali, so the transcript was also meaningless). In the real app:
  load the model once, feed one short utterance at a time, and create one recognizer per utterance.
- **Groq (online alternative).** `whisper-large-v3-turbo` transcribed the same 24-minute file in about 8 s. Free plan: 20 requests/min, 2,000 requests/day, 7,200 audio seconds/hour, 28,800 audio seconds/day. Always pass the language: auto-detect picked the wrong language on this audio.
- **WER is a rough guide.** Hinglish spelling varies. Numbers, names and English words (for example "gym", "9:30", "Pune") still need to be checked by hand.
- **Linux only.** The benchmark ran on Linux. `bench.py` and `long.py` use the `resource` module, which does not exist on Windows. To rerun on Windows, replace it with
  `psutil.Process().memory_info().peak_wset`.

## Files

| File | What it does |
|---|---|
| `bench.py` | Runs one model on all clips: speed, peak RAM, WER. Writes `results/out_<model>.json`. Usage: `python bench.py collabora` (models: `vosk-hi`, `collabora`, `hinglish`). |
| `score_roman.py` | Re-scores the `out_*.json` files in a shared Roman space and runs the control check. |
| `bench_long.py` | Runs one model on one long audio file and prints peak memory. Takes the audio path as an argument. |
| `bench_vosk_long.py` | Optional. Vosk on the 24-minute file, memory logged every minute. |
| `clips/` | Test clips (`NN.wav`) and their reference text (`NN.txt`). |
| `results/` | Output JSON files. Not committed. |

## Models (not committed, download again to rerun)

- Vosk: `vosk-model-small-hi-0.22` from https://alphacephei.com/vosk/models, unzip to `models/vosk-hi/`.
- Collabora: `collabora/whisper-tiny-hindi` from Hugging Face, converted for faster-whisper:
  `ct2-transformers-converter --model collabora/whisper-tiny-hindi --output_dir models/collabora --copy_files tokenizer.json preprocessor_config.json --quantization int8`
- whisper-tiny-hinglish: `abhishekgautamm/whisper-tiny-hinglish` on Hugging Face (rejected).

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install faster-whisper vosk jiwer soundfile indic-transliteration psutil
```

## Next

TTS comparison (Piper, Kokoro, Paradee) is a separate step: 5 short Friend replies, scored by ear, with time to first audio and RAM.
