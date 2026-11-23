# Capstone: Personal Voice Assistant

A personal assistant ("friend") backend built with FastAPI and PostgreSQL. You can talk to it by text or by voice. It remembers your reminders and check-ins (meals, gym, sleep, mood), searches your saved notes, and keeps one conversation per day.

## How it fits together

```
browser (static/)  ──►  FastAPI (app/main.py)
                          ├─ /chat       text ──► Brain (agent) ──► answer
                          ├─ /voice      WAV ──► STT ──► Brain ──► TTS ──► WAV
                          ├─ /reminders, /checkins   plain CRUD
                          └─ /warmup, /health, /health/db

Brain (app/harness/brain.py)   one agent, history saved in Postgres per day
Tools (app/agent/tools.py)     reminders, check-ins, notes search, current time
Tracker (app/tracker.py)       the one place that owns reminder and check-in SQL
services/stt, tts, embed       separate speech and embedding services (HTTP)
rag/                           saved-notes search
```

The agent can add and list reminders and check-ins, but it has no delete tool. Only the HTTP route can delete a reminder, and a test enforces this.

## Install

You need [uv](https://docs.astral.sh/uv/) and a PostgreSQL database with the pgvector extension (the CI image is `pgvector/pgvector:pg18`).

```bash
uv sync
```

Create the tables by running the schema against your database:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

Or use Docker, which starts the API and PostgreSQL together (set `POSTGRES_PASSWORD` in `.env`) and creates the tables from `db/schema.sql` on first start:

```bash
docker compose up --build
```

To rebuild the tables, remove the database volume with `docker compose down -v`.

If you already have a database from an older version, note that `reminders.due_at` is now `timestamptz`. `db/fix_tz.sql` converts an old column. Run it once only, because it shifts times if applied twice.

## Configure

Create a `.env` file in the project root. Never commit it. The app reads these when it starts, so a missing one stops it with a `KeyError`.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | connection string for the app's database |
| `TEST_DATABASE_URL` | connection string for the test database. Tests empty its tables, so never point it at real data |
| `AGENT_MODEL` | model the agent uses (a pydantic-ai model name) |
| `API_KEY` | key clients send in the `x-api-key` header. If it is empty or unset, every request is rejected |
| `HEALTH_KEY` | key for `/health/db`, sent in the `x-health-key` header |
| `STT_URL`, `STT_KEY` | speech-to-text service and its key |
| `TTS_URL`, `TTS_KEY` | text-to-speech service and its key |
| `TTS_RATE` | optional, TTS sample rate, default `22050` |
| `EMBED_URL`, `EMBED_KEY` | embedding service and its key |
| `LOGFIRE_TOKEN` | optional. Without it, no telemetry is sent |
| `OPENROUTER_API_KEY` | key for the notes search and the experiments in `notebook/` |

## Run

```bash
uv run fastapi dev app/main.py
```

- The web app is at http://127.0.0.1:8000/ and the interactive API page at http://127.0.0.1:8000/docs.
- `GET /warmup` wakes the database and the STT, TTS and embedding services. Call it before you start talking, because cold services are slow.
- The speech services have their own folders in `services/` and run separately.

## Call the API

Every route except `/health` needs the key:

```powershell
$h = @{ "x-api-key" = "your-api-key" }
```

Chat:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -Headers $h `
  -ContentType "application/json" -Body '{"message": "remind me to stretch tomorrow at 9am"}'
```

Voice: send a mono, 16-bit, 16000 Hz WAV to `POST /voice`. You get a WAV back, with the time spent in each step in the `X-Time-STT`, `X-Time-Agent` and `X-Time-TTS` headers.

Reminders and check-ins:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/reminders -Headers $h `
  -ContentType "application/json" `
  -Body '{"title": "Gym session", "due_at": "2026-11-30T18:30:00", "lead_minutes": 30}'

Invoke-RestMethod -Uri http://localhost:8000/reminders -Headers $h
Invoke-RestMethod -Method Delete -Uri http://localhost:8000/reminders/1 -Headers $h

Invoke-RestMethod -Method Post -Uri http://localhost:8000/checkins -Headers $h `
  -ContentType "application/json" -Body '{"kind": "meal", "note": "dal rice"}'
Invoke-RestMethod -Uri http://localhost:8000/checkins -Headers $h
```

`kind` must be one of `meal`, `gym`, `sleep`, `mood`. `lead_minutes` must be between 0 and 240. A `due_at` without a timezone is treated as India time (IST).

## Test

```bash
uv run python -m pytest -v
```

Tests use the `friend_test` database, which is emptied before each test. Make sure `TEST_DATABASE_URL` points to it. The tests set their own `API_KEY`, so your `.env` value does not matter.

`tests/check_*.py` are manual scripts, not tests. They need real services, and `check_voice.py` records from your microphone.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request:

1. `ruff check .`
2. load `db/schema.sql` into a Postgres service
3. `pytest`, with dummy values for the service URLs and keys (no network calls)
4. a gitleaks secret scan

## Docs

- `CODEBASE_SUMMARY.md`: a tour of the code
- `docs/`: design notes, such as the model choice
