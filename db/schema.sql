create table if not exists reminders (
    id serial primary key,
    title text not null,
    due_at timestamp not null,
    lead_minutes integer default 10 not null check (lead_minutes >= 0 and lead_minutes <= 240),
    status text default 'pending' not null check (status in ('pending', 'done', 'missed'))
);

create table if not exists checkins (
    id serial primary key,
    kind text not null check (kind in ('meal', 'gym', 'sleep', 'mood')),
    note text not null,
    at timestamp not null default now()
);

create table if not exists cost_events (
    id serial primary key,
    at timestamp not null default now(),
    model text not null,
    input_tokens integer not null,
    output_tokens integer not null,
    cost_usd numeric not null
);

CREATE EXTENSION IF NOT EXISTS vector;

create table if not exists chat_runs (
    id bigserial primary key,
    session_id text not null,
    messages jsonb not null,
    created_at timestamptz not null default now()
);
create index if not exists chat_runs_session_idx on chat_runs (session_id, id desc);