# Reminders API (M0.2)

Base URL when running locally: `http://localhost:8000`. Interactive docs: `/docs`.
All times are local time with no time zone, in ISO format, for example `2026-11-10T18:00:00`.

## Data shapes

**Reminder**

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Set by the server. Only in responses. |
| `title` | string | 1 to 200 characters |
| `due_at` | datetime | Required |
| `lead_minutes` | integer | 0 to 240. Default 10. The user is notified this many minutes before `due_at`. |
| `status` | string | `pending`, `done` or `missed`. Default `pending`. |

**CheckIn**

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Set by the server. Only in responses. |
| `kind` | string | `meal`, `gym`, `sleep` or `mood` |
| `note` | string | Required |
| `at` | datetime | Optional. Defaults to the time of the request. |

## Routes

| Method | Path | What it does | Success | Errors |
|---|---|---|---|---|
| POST | `/reminders` | Create a reminder | 201, returns the reminder with its `id` | 422 if a field is invalid |
| GET | `/reminders` | List all reminders, earliest `due_at` first | 200, a list | none |
| DELETE | `/reminders/{id}` | Delete one reminder | 204, no body | 404 if the id does not exist, 422 if the id is not a number |
| POST | `/checkins` | Record a check-in | 201, returns the check-in with its `id` | 422 if a field is invalid |
| GET | `/checkins` | List all check-ins, oldest first | 200, a list | none |

## Examples

Create a reminder:

```http
POST /reminders
Content-Type: application/json

{"title": "Call mom", "due_at": "2026-11-10T18:00:00", "lead_minutes": 10}
```

Response (201):

```json
{"id": 1, "title": "Call mom", "due_at": "2026-11-10T18:00:00", "lead_minutes": 10, "status": "pending"}
```

A lead time above 240 is rejected with 422, and nothing is saved:

```json
{"title": "Call mom", "due_at": "2026-11-10T18:00:00", "lead_minutes": 300}
```

Record a check-in:

```http
POST /checkins
Content-Type: application/json

{"kind": "meal", "note": "poha at 9"}
```

## Notes

- Validation happens twice: in the Pydantic models, and again in the database (`CHECK` constraints on `lead_minutes`, `status` and `kind`).
- There is no update route yet. To change a reminder, delete it and create a new one.
- There is no authentication. Do not expose the API to the internet until there is.
