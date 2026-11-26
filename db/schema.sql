create table if not exists reminders (
    id serial primary key,
    title text not null,
    due_at timestamptz not null,
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

create table if not exists friend_tool_spills (
    handle text primary key,
    data bytea not null,
    created_at timestamptz not null default now()
);

CREATE UNIQUE INDEX IF NOT EXISTS reminders_no_dupes
ON reminders (lower(text), remind_at)
WHERE sent_at IS NULL;