alter table reminders
    alter column due_at type timestamptz using due_at at time zone 'UTC';