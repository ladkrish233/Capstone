# Codebase Summary

Project: "Friend", a voice assistant for reminders, check-ins and personal notes.
Branch when this was written: `tts-service`. Many files are not committed yet (see section 10).

How this was made: I read the code. I did not run the services. I did not read `.env` or any secret.
I ran `ruff check` once (read only). I did not read `docs/*`, `notebook/*` or `rag/evals/*` in detail.

## 1. Folder tree

```
Capstone/
├── app/                 API (FastAPI) + agent
│   ├── main.py          Routes: health, reminders, checkins, chat
│   ├── voice.py         Route: POST /voice (calls stt, agent, tts)
│   ├── agent.py         pydantic-ai agent and its tools
│   ├── security.py      check_key(): compares a header to an env var
│   ├── db.py            SQL helpers for the REST routes (psycopg)
│   ├── models.py        Pydantic models: Reminder, CheckIn, ChatRequest, ChatResponse
│   └── cost.py          Token price math (used only by notebooks)
├── prompts/             System prompts friend_v1..v4.md (v4 is loaded)
├── rag/                 Notes: load, chunk, embed, search
│   ├── ingest.py        Loaders: md, txt, pdf, csv, docx, html
│   ├── chunk.py         Splits docs into chunks
│   ├── store.py         Postgres pgvector store (used by the agent)
│   ├── remote_embed.py  Client for the embed service
│   ├── knowledge.py     search_notes(): what the agent tool calls
│   ├── embed.py         OLD: OpenRouter embeddings
│   ├── search.py        OLD: in-memory store, cached in data/cache/store.json
│   └── evals/           questions.jsonl + run.py (not reviewed)
├── services/
│   ├── embed/           Embedding service (EmbeddingGemma ONNX)
│   ├── stt/             Speech-to-text service (Vosk)
│   └── tts/             Text-to-speech service (Piper, Hindi)
├── db/                  schema.sql, fix_tz.sql
├── data/                notes/ (about 60 .md files), cache/store.json (3.3 MB)
├── tests/               test_api.py, test_models.py, test_voice.py, conftest.py, fixtures/
├── notebook/            Course/demo scripts (llm101, rag_demo, tools_demo, ...)
├── docs/                Notes and write-ups (api, model-choice, stt-bench, ...)
├── stt-bench/           STT benchmark files (git-ignored)
├── tts-samples/         Local audio samples (untracked)
├── .github/workflows/ci.yml   CI
├── Dockerfile, docker-compose.yml   API + Postgres in containers
├── apply_sql.py         Runs a .sql file against DATABASE_URL (git-ignored)
├── pyproject.toml, uv.lock, .python-version
└── new.wav, out.wav, out.pcm, sent.wav   Stray audio files in the root (untracked)
```

## 2. Services and how they connect

```
client --X-Api-Key--> api (app/) --X-STT-Key--> stt   /transcribe
                        |        --X-TTS-Key--> tts   /speak/stream
                        |--> agent (LLM via AGENT_MODEL)
                        |--> Postgres (reminders, checkins) 
                        '--> rag/store.py --X-Embed-Key--> embed /embed
                                          --> Postgres table "chunks" (pgvector)
```

Deploy: each service folder has a `.fastapicloud/` folder, so each is linked to FastAPI Cloud.
The docs say STT was tested on a FastAPI Cloud "Nano" box (0.1 vCPU, 500 MB, us-east-1).
The TTS README also mentions Vercel. The database looks like Neon (see `notebook/neon_test.py`).
The root `.fastapicloud/` links the api. The api also has a Dockerfile (incomplete, see section 10).

### api
- Folder: `app/`. Entry: `app.main:app`.
- Auth: `X-Api-Key` (env `API_KEY`). `/health/db` uses `X-Health-Key` (env `HEALTH_KEY`).
- Routes: section 3.

### stt (`services/stt/main.py`)
- Auth header: `X-STT-Key` (env `STT_KEY`). WebSocket: `?key=` query param or first text message.
- `GET /health`: no key. Returns `{"ok": true}` or 503.
- `POST /transcribe?words=false&lang=hi|en`
  - Request body: WAV (mono, 16-bit, 16 kHz) or raw PCM16 bytes. Max 30 s.
  - Response: `{"text": str, "ms": int}`.
  - Errors: 401 bad key, 413 too long, 415 wrong format, 503 model not loaded.
- `WS /ws?lang=`: binary PCM16 frames in. Text `end` finishes.
  Out: `{"type":"partial","text"}` then `{"type":"final","text","ms"}`.
- Loads one Vosk model per process: `hi` (default) or `en`, or `both` for tests.
- The api does not use the WebSocket.

### tts (`services/tts/main.py`)
- Auth header: `X-TTS-Key` (env `TTS_KEY`).
- `GET /health`: no key. `{"ok": bool}`.
- `POST /speak` body `{"text": str, "translit": bool=false}`. Returns a WAV. Headers: `X-Sample-Rate`, `X-Pieces`, `X-RTF`.
- `POST /speak/stream`: same body. Returns raw PCM16 mono (`application/octet-stream`). Header `X-Sample-Rate`.
- `GET /stock/{name}`: fixed Hindi phrases (`ek-minute`, `haan-bolo`, `namaste`, ...). Returns a WAV.
- `GET /stats`, `POST /stats/reset-peak`: memory and cache numbers.
- Max 600 chars per request (413 if longer). Text is split in `chunker.py`. PCM is cached (24 MB LRU).
- `translit=true` turns Roman Hinglish into Devanagari (`translit.py`).
- Voice: `hi_IN-rohan-medium`. The model file is not in git. If missing, it downloads from Hugging Face at start.
- This service is excluded from the root uv workspace.

### embed (`services/embed/main.py`)
- Auth header: `X-Embed-Key` (env `EMBED_KEY`).
- `GET /health`: no key. `{"ok": bool}`.
- `POST /embed` body `{"texts": [str] (1 to 16), "kind": "query"|"document"}`.
  Response `{"embeddings": [[float x768]], "dims": 768}`. Each text max 2000 chars.
- Model: `onnx-community/embeddinggemma-300m-ONNX`, q4 file. Vectors are normalised.

## 3. The api app

Both `app/main.py` and `app/voice.py`. "Key" is `check_key(header, env_name)`.
It returns 401 if the env var is empty or the header does not match.

| Method + path | What it does | Key check | Calls |
|---|---|---|---|
| GET `/health` | Returns `{"status":"ok"}` | none | none |
| GET `/health/db` | `select 1`, returns `{ok, ms}`. 503 on error | `X-Health-Key` / `HEALTH_KEY` | `get_db_health` |
| POST `/reminders` (201) | Saves a reminder. Body: `title`, `due_at`, `lead_minutes` (0-240, default 10), `status` | `X-Api-Key` | `add_reminder` (db.py) |
| GET `/reminders` | Lists all, ordered by `due_at` | `X-Api-Key` | `list_reminders` |
| DELETE `/reminders/{id}` (204) | Deletes one. 404 if missing | `X-Api-Key` | `delete_reminder` |
| POST `/checkins` (201) | Saves a check-in. Body: `kind` (meal, gym, sleep, mood), `note`, optional `at` | `X-Api-Key` | `add_checkin` |
| GET `/checkins` | Lists all, newest first | `X-Api-Key` | `list_checkins` |
| POST `/chat` | Body `{message (1-1000 chars), session_id="main"}`. Runs the agent. Returns `{answer}`. 502 if the agent fails | `X-Api-Key` | `agent.run` |
| POST `/voice` (voice.py) | Body: WAV mono 16-bit 16 kHz, max 2,000,000 bytes. Calls stt, then agent, then tts. Returns `audio/wav` with `X-Time-STT/Agent/TTS` headers. 422 if no speech. 502 if a service fails | `X-Api-Key` | `call()` to `{STT}/transcribe`, `agent.run`, `call()` to `{TTS}/speak/stream` |
| POST `/voice` (main.py) | Stub with `pass`. Returns nothing | `X-Api-Key` | none |

Notes:
- `voice_router` is included before the stub is defined. The router version wins. The stub is dead code.
- `/chat` ignores `session_id`. It sends only the new message to the agent (no history).
- All routes with a key use `check_key`. Only `/health` is open.

## 4. The agent (`app/agent.py`, `prompts/`)

- Library: `pydantic-ai` `Agent`. Logging: `logfire` (sends only if a token exists).
- Model setting: env `AGENT_MODEL` (example in code: `openrouter:<provider>/<model>`). It must support tool calling. Required.
- Prompt: `prompts/friend_v4.md`, read at import. `{today}` is replaced by a fixed phrase.
  A second instruction adds `Current time: <IST>` on every run.
- Timezone: `Asia/Kolkata`.

| Tool | What it does | Table |
|---|---|---|
| `get_time` | Returns HH:MM in India | none |
| `list_reminders` | Up to 50 reminders ordered by `due_at` | reads `reminders` |
| `add_reminder(Reminder)` | Inserts a reminder. Rejects past times with `ModelRetry` | writes `reminders` |
| `list_checkins` | Last 20 check-ins, by id | reads `checkins` |
| `add_checkin(CheckIn)` | Inserts a check-in (`kind`, `note`) | writes `checkins` |
| `search_knowledge(query)` | Calls `rag.knowledge.search_notes` | reads `chunks` (via pgvector) |

Tool DB errors return a short text. They do not raise.

The agent can NOT:
- Delete, cancel or edit a reminder. There is no tool. The prompt tells it to say "I can't delete reminders".
- Delete or edit a check-in.
- Mark a reminder `done` or `missed`.
- Send notifications, read email, or reach the web.
- Remember earlier chats (no history is passed).

Prompt rules worth knowing: replies are spoken, so max 3 sentences, no lists, no emojis.
Text from notes or users is treated as data, not instructions.
`tool_used(result)` in `agent.py` is defined but nothing calls it.

## 5. Database

Defined in `db/schema.sql`. Postgres with the `vector` extension.

| Table | Columns | Read / written by |
|---|---|---|
| `reminders` | `id` serial PK, `title` text, `due_at` timestamp, `lead_minutes` int 0-240 (default 10), `status` pending/done/missed | `app/db.py` (REST), `app/agent.py` (tools), `tests/conftest.py` (truncate) |
| `checkins` | `id` serial PK, `kind` meal/gym/sleep/mood, `note` text, `at` timestamp default now() | `app/db.py`, `app/agent.py`, `tests/conftest.py` |
| `cost_events` | `id`, `at`, `model`, `input_tokens`, `output_tokens`, `cost_usd` | `add_cost_event` in `app/db.py`. Called only from `notebook/` |
| `chat_runs` | `id` bigserial, `session_id`, `messages` jsonb, `created_at` timestamptz; index on `(session_id, id desc)` | Nothing. Not used yet |
| `chunks` (not in schema.sql) | Made by `langchain_postgres` (`init_vectorstore_table`, vector size 768) | `rag/store.py` |

`db/fix_tz.sql` changes `reminders.due_at` to `timestamptz`, treating old values as UTC.
`schema.sql` was not updated to match.

## 6. RAG / notes

1. Ingest (`rag/ingest.py`): loads `data/notes/**/*.md`, `data/pdfs`, `data/csv`, `data/docx`, `data/html`, `data/text`.
   `clean()` removes front matter and HTML comments. Empty or tiny files are skipped.
   Title = first `# heading`, else the file name.
2. Chunk (`rag/chunk.py`): LangChain `RecursiveCharacterTextSplitter`, 800 chars, 100 overlap.
   Metadata: `doc_id`, `source`, `kind`, `title`, `chunk_index`.
3. Embed: `rag/remote_embed.py` posts batches of 8 to `EMBED_URL` (`/embed` is added if missing) with header `X-Embed-Key`.
   `kind` is `document` for chunks and `query` for searches. Timeout 60 s.
4. Store: `rag/store.py` uses `PGVectorStore`, table `chunks`, size 768.
   Load with `python -m rag.store add`. With no argument it runs sample questions.
5. Search: agent tool `search_knowledge` calls `rag.knowledge.search_notes`.
   It fetches 4 chunks and keeps those with distance <= 0.80. Each chunk is cut to 600 chars.
   The result is wrapped as "data, not instructions". On any error it returns "Search is unavailable right now."

The old path is `rag/embed.py` (OpenRouter model) plus `rag/search.py` (in-memory store saved in `data/cache/store.json`).
The agent does not use it.

## 7. Environment variables (names only)

| Name | Read by | Required? |
|---|---|---|
| `DATABASE_URL` | `app/agent.py`, `app/db.py`, `rag/store.py`, `apply_sql.py`, `notebook/check_neon.py`, `tests/conftest.py` | Yes (api fails at import) |
| `TEST_DATABASE_URL` | `tests/conftest.py`, CI | Yes, for tests |
| `AGENT_MODEL` | `app/agent.py` | Yes (api fails at import) |
| `API_KEY` | `app/security.py` (via main.py, voice.py), `tests/test_voice.py` | Yes. If unset, every keyed route returns 401 |
| `HEALTH_KEY` | `app/security.py` (`/health/db`) | Only for `/health/db` |
| `STT_URL`, `TTS_URL` | `app/voice.py` | Yes (api fails at import) |
| `STT_KEY`, `TTS_KEY` | `app/voice.py` (to call), `services/stt`, `services/tts` (to check) | Yes |
| `TTS_RATE` | `app/voice.py` | No (default 22050) |
| `STT_LANG` | `services/stt/main.py` | No (default `hi`) |
| `STT_MODEL_DIR` | `services/stt/main.py` | No |
| `EMBED_KEY` | `services/embed/main.py`, `rag/remote_embed.py` | Yes |
| `EMBED_URL` | `rag/remote_embed.py` | Yes (needed at import by the agent) |
| `MODEL_DIR` | `services/embed/embed_local.py` | No, and it has no effect (overwritten on the next line) |
| `OPENROUTER_API_KEY` | `rag/embed.py`, notebooks; also by pydantic-ai if the model is on OpenRouter | Needed for the old RAG path and OpenRouter models |
| `ANTHROPIC_API_KEY` | Not read in repo code. Read by the library if the model is Anthropic | Depends on `AGENT_MODEL` |
| `LOGFIRE_TOKEN` | Read by `logfire` | No |
| `PYDANTIC_AI_NO_BANNER` | Library | No |
| `POSTGRES_PASSWORD` | `docker-compose.yml` | Yes for compose |
| `NEON_DATABASE_URL` | `notebook/neon_test.py` | Notebook only |
| `PINECONE_API_KEY` | In `.env.example` only. Nothing reads it | No |

`.env.example` lists only 5 names. Most names above are missing from it.

## 8. Tests and CI

Tests (`tests/`, `pytest`, `pythonpath=["."]`):
- `test_models.py`: 6 tests on `Reminder` and `CheckIn`. They need no database or keys.
- `test_api.py`: 7 tests on `/reminders` and `/checkins` with `TestClient` and a real Postgres.
- `conftest.py`: sets `DATABASE_URL` from `TEST_DATABASE_URL` and truncates `reminders`, `checkins` before each test.
- `test_voice.py`: not a real test. It records from the microphone and posts to `localhost:8000/voice` at import time.
- No tests for `/chat`, `/voice`, the agent, RAG or the three services.

CI (`.github/workflows/ci.yml`), on every push and PR:
1. Job `checks` (Postgres `pgvector/pgvector:pg18`): `uv sync --frozen`, `ruff check .`, `alembic upgrade head`, `pytest -q`.
2. Job `secret-scan`: gitleaks. `.gitleaks.toml` allows `.env.example`.

Likely failing:
- `ruff check .` reports 22 errors locally (unused imports in `app/main.py`, duplicate dict keys in `services/tts/translit.py`, unsorted imports).
- `alembic upgrade head` cannot work. Alembic is not a dependency and there is no alembic config. The schema is never applied in CI.
- `test_api.py` never sends `X-Api-Key`. Every keyed call returns 401, so these tests fail even with `API_KEY` set.
- `app.main` needs `AGENT_MODEL`, `STT_URL`, `TTS_URL`, `STT_KEY`, `TTS_KEY` at import. CI sets none, so `test_api.py` fails at import.
- `test_voice.py` imports `sounddevice`, which is not a dependency. It would break collection.
- `test_models.py` should pass.

## 9. Dependencies and Python version

| Project | Python | Main dependencies |
|---|---|---|
| Root (`pyproject.toml`, `.python-version` = 3.13) | `>=3.13` | fastapi[standard], pydantic-ai[slim], pydantic-evals, langchain (+anthropic, openai, postgres, text-splitters), psycopg[binary], pandas, pypdf, python-docx, beautifulsoup4, lxml, numpy, onnxruntime, tokenizers, huggingface-hub, python-dotenv, fastapi-cloud-cli. Dev: pytest, ruff |
| `services/embed` (`.python-version` = 3.13) | `>=3.13,<3.14` | fastapi[standard], fastapi-cloud-cli, huggingface-hub, numpy, onnxruntime, tokenizers, uvicorn[standard]. It is a root workspace member. It also has an exported `requirements.txt` |
| `services/stt` (`.python-version` = 3.13) | `>=3.13,<3.14` | fastapi[standard], vosk. Its own workspace root, own `uv.lock` |
| `services/tts` (`.python-version` = 3.13) | `>=3.13,<3.14` | fastapi[standard], onnxruntime, numpy, piper-tts, indic-transliteration. Own `uv.lock`, excluded from root workspace |
| Docker image | `python:3.13-slim` | Installs the root lock without dev |

Imported but not declared in the root `pyproject.toml`: `logfire`, `httpx`, `requests` (they arrive through other packages), and `sounddevice` (not in the lock at all).
`[project.scripts] capstone = "capstone:main"` points to a module that does not exist.

## 10. Known problems

Security and auth
- `services/embed` compares the key with `!=`, not a constant-time compare. The other services use `hmac.compare_digest`.
- The STT WebSocket takes the key in the URL query. URLs often end up in logs.
- Almost all work is untracked or modified (`app/agent.py`, `app/security.py`, `app/voice.py`, `services/stt/`, large `models/` folders). `services/embed/models/` and `services/stt/models/` should not be committed.
- Everyone shares one `API_KEY`. There is no user id in any table.

Routes and logic
- Duplicate `POST /voice`: the stub in `main.py` is dead code.
- `/chat` accepts `session_id` but ignores it. `chat_runs` and `tool_used` are unused.
- Time zones: `db.py` writes `due_at` as given (naive from REST). The agent writes IST-aware values. After `fix_tz.sql` the column is `timestamptz`, and a naive REST value is read in the database session zone (often UTC). Reminders from REST and from the agent can differ by 5.5 hours. `schema.sql` still says `timestamp`.
- `CheckIn.at` defaults to server local time (naive).
- `voice.py` hard-codes `TTS_RATE` (22050). The TTS service already returns `X-Sample-Rate`.
- `voice.py` does not set `translit`. The prompt is English and the voice is Hindi. English output may sound wrong. Check this by ear.
- TTS limit is 600 chars. A longer agent answer gives 413 from tts, which the api reports as 502.
- `voice.py` allows 2,000,000 bytes (about 62 s). STT allows 30 s. A long clip gives 502.
- `wave.open` in `voice.py` is not wrapped. A non-WAV body raises `wave.Error` and returns 500.
- `/voice` has no timeout around the agent call.
- `embed` `dims` is hard-coded to 768. `MAX_LEN`, batch size 16 and 2000 chars are hard-coded in several places.
- `embed_local.py`: `MODEL_DIR` from env is overwritten on line 13. A comment says "lower to 256 if the Nano runs out of memory".
- STT loads one language per process. The api never passes `lang`.
- `knowledge.py` uses `print` for errors, not logging.

Imports and names
- `app/main.py` has unused imports: `os`, `secrets`, `asyncio`, `APIRouter`, `httpx`. It also imports `CheckIn` and `Reminder`, which are used.
- Typos: `"agent unavailabe"` (main.py), `"No relavant notes found."` (knowledge.py), `embed_docments` (rag/embed.py), `lifeapp`, `"table already exists,skippings"`.
- `services/tts/translit.py` repeats the keys `"kar"`, `"do"`, `"abhi"` in a dict (later value wins).
- `services/tts/chunker.py` docstring says 100-120 chars. `MAX_LEN` is 90.
- Two function names collide in meaning: `list_reminders` / `add_reminder` exist in both `app/db.py` and `app/agent.py`. Agent and REST use different SQL (REST returns all rows; agent limits 50).
- `.gitignore` has a missing newline: `tricky_out.txtstt-bench/` is one broken entry. `.dockerignore` and `apply_sql.py` are git-ignored.
- `tests/test_voice.py` runs hardware code at import.
- `rag/embed.py` needs `OPENROUTER_API_KEY` at import. `rag/search.py` imports it.
- `reply.wav`, `new.wav`, `out.wav`, `out.pcm`, `sent.wav` are loose in the project folder.

Docker and deploy
- The Dockerfile copies only `app/` and `rag/`. It does not copy `prompts/`. `app/agent.py` reads `prompts/friend_v4.md` at import, so the container fails to start.
- `docker-compose.yml` mounts `schema.sql` only on first database start. It does not apply later changes.
- `data/cache/store.json` (3.3 MB, embeddings from the old path) is committed.
- `docs/` and `README.md` still describe an earlier stage ("voice and LLM parts come later"). README lists 4 env vars.

Error handling gaps
- REST routes in `main.py` (except `/health/db`) do not catch database errors. A DB failure returns a raw 500.
- `app/db.py` opens a new connection per call. No pool.
- `/chat` returns 502 for any agent error, including bad input.

## 11. What is NOT built yet

- Chat sessions or history (`chat_runs` table exists, no code uses it).
- Long-term memory of the user.
- Notification or push sending. `notify_at` is computed, but nothing sends or schedules it.
- A job that moves reminders to `done` or `missed`.
- Agent tools to cancel, edit or complete reminders (blocked on purpose in the prompt, but the REST API can delete).
- Any UI, PWA or mobile client. Only `tests/test_voice.py` as a mic test.
- Streaming voice through the api. The STT WebSocket and TTS stream exist, but `/voice` is one request and one WAV reply.
- User accounts or per-user data.
- A migration tool (CI calls alembic, nothing is set up).
- An endpoint or job to ingest notes. Ingestion is a manual command.
- Cost tracking in the live api. `cost_events` is written only by notebooks.
- Tests for the agent, RAG, `/chat`, `/voice` and the three services.
- A working Docker image for the api.

## How to run it locally

```bash
# 1. install
uv sync

# 2. database (needs POSTGRES_PASSWORD in .env), then schema
docker compose up -d db
uv run python apply_sql.py db/schema.sql
uv run python apply_sql.py db/fix_tz.sql

# 3. services, each in its own terminal (set the *_KEY env vars first)
cd services/embed && uv run uvicorn main:app --port 8001
cd services/stt   && uv run uvicorn main:app --port 8002
cd services/tts   && uv run uvicorn main:app --port 8003

# 4. load notes into pgvector (needs EMBED_URL, EMBED_KEY, DATABASE_URL)
uv run python -m rag.store add

# 5. api (needs DATABASE_URL, AGENT_MODEL, API_KEY, HEALTH_KEY,
#         STT_URL, STT_KEY, TTS_URL, TTS_KEY in .env)
uv run fastapi dev app/main.py

# 6. try it
curl -H "X-Api-Key: $API_KEY" -H "Content-Type: application/json" \
     -d '{"message":"what reminders do I have?"}' http://127.0.0.1:8000/chat

# tests and lint
uv run pytest -q
uv run ruff check .
```

Before step 3 for tts: download the voice model as described in `services/tts/README.md`.
