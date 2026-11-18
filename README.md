# Capstone: Reminders and Check-ins API

A personal voice assistant project. This part is the backend API: it stores reminders and daily check-ins (meals, gym, sleep, mood) in PostgreSQL, and exposes them over HTTP with FastAPI. The voice and LLM parts are built on top of this API in later stages.

## Install

You need [uv](https://docs.astral.sh/uv/) and, for the Docker option, Docker Desktop.

Local install:

```bash
uv sync
```

Docker install (runs the API and PostgreSQL together):

```bash
docker compose up --build
```

## Configure

Copy `.env.example` to `.env` and fill in the values. Never commit `.env`.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | connection string for the app's database |
| `TEST_DATABASE_URL` | connection string for the test database (`friend_test`) |
| `POSTGRES_PASSWORD` | password for the PostgreSQL container, used by Docker Compose |
| `OPENROUTER_API_KEY` | key for the LLM experiments in `notebook/` |

## Run

Locally, with a PostgreSQL database running and `DATABASE_URL` set:

```bash
uv run fastapi dev app/main.py
```

Then open http://127.0.0.1:8000/docs for the interactive API page.

With Docker, the API is at http://localhost:8000/docs.

The database tables are created from `schema.sql` the first time the database starts. To rebuild them, remove the database volume with `docker compose down -v`.

## Test

Tests use the `friend_test` database, which is emptied before each test. Make sure `TEST_DATABASE_URL` points to it, not to `friend`.

```bash
uv run python -m pytest -v
```

## Call the API

Create a reminder:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/reminders `
  -ContentType "application/json" `
  -Body '{"title": "Gym session", "due_at": "2026-11-10T18:30:00", "lead_minutes": 30}'
```

List reminders:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/reminders
```

Delete a reminder by id:

```powershell
Invoke-RestMethod -Method Delete -Uri http://localhost:8000/reminders/1
```

Record a check-in:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/checkins `
  -ContentType "application/json" `
  -Body '{"kind": "meal", "note": "dal rice"}'
```

List check-ins:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/checkins
```

`kind` must be one of `meal`, `gym`, `sleep`, `mood`. `lead_minutes` must be between 0 and 240.