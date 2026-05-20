# morty — Nail Salon Voice Agent

## Project Overview

Voice agent for nail salon booking. Twilio handles PSTN. AssemblyAI Voice Agent API handles STT + LLM + TTS. Python FastAPI tool-server handles all business logic. SQLite is the only database.

## Repository Layout

```
untitled folder copy/
├── morty/
│   ├── tool-server/      # YOU BUILD THIS — Python FastAPI + SQLite
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   ├── scheduler.py
│   │   ├── seed.py
│   │   └── tools/
│   │       ├── crud.py
│   │       ├── search.py
│   │       ├── customers.py
│   │       ├── services.py
│   │       └── callbacks.py
│   └── bridge/           # PARTNER BUILDS — TypeScript Twilio ↔ AssemblyAI
│       ├── server.ts
│       ├── twilio.ts
│       ├── assemblyai.ts
│       └── tool-dispatcher.ts
└── src/                  # OLD STACK — do not touch, scheduled for deletion
```

## Stack

| Layer | Tech |
|-------|------|
| Phone/PSTN | Twilio Voice |
| Voice Agent | AssemblyAI Voice Agent API (`wss://agents.assemblyai.com/v1/ws`) |
| Bridge | TypeScript + Express + ws |
| Tool Server | Python 3.11+ + FastAPI |
| Database | SQLite (`morty.db`) |
| Scheduler | APScheduler (reminder calls) |

## Tool-Server: Run

```bash
cd morty/tool-server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Tool-Server: Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools/schemas?role=consumer` | AssemblyAI tool definitions for consumer role |
| GET | `/tools/schemas?role=owner` | AssemblyAI tool definitions for owner role |
| POST | `/tools/{tool_name}` | Execute any tool with JSON body |
| GET | `/sessions/role?phone={phone}` | Detect caller role (consumer vs owner) |
| GET | `/health` | Health check |

## Tool-Server: All Tools

### Consumer (9)
- `search_customer` — lookup by phone or name
- `get_appointment` — fetch by ID
- `list_services` — all nail services + prices
- `check_service` — single service details
- `check_inventory` — is a nail color in stock
- `list_available_slots` — open booking slots for a date
- `book_appointment` — create new appointment
- `modify_appointment` — change datetime/service/color
- `cancel_appointment` — cancel by ID
- `request_callback` — log callback for staff
- `hang_up` — signal end of call

### Owner (additional 6)
- `list_today_appointments`
- `update_appointment_status`
- `list_pending_callbacks`
- `resolve_callback`
- `trigger_reminder_call`
- `append_appointment_note`

## Bridge → Tool-Server HTTP Contract

```
POST http://localhost:8000/tools/{tool_name}
Content-Type: application/json
{ ...tool_arguments }   ← from tool.call.arguments (already parsed)

→ 200: { ...result }    ← bridge JSON.stringify() this for tool.result.result
→ 4xx/5xx: { "error": "..." }
```

Bridge fetches schemas on startup:
```
GET http://localhost:8000/tools/schemas?role={role}
→ [{ type, name, description, parameters }, ...]
```

## AssemblyAI Auth

```
Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31
```

Bearer prefix **required** for Voice Agent API (different from STT).

## Environment Variables (tool-server/.env)

```
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
TWILIO_WEBHOOK_BASE=
OWNER_PHONE_NUMBER=
DB_PATH=morty.db
PORT=8000
```

## SQLite Tables

`customers`, `services`, `inventory`, `appointments`, `callbacks`, `sessions`

See `morty/SCHEMA.md` for full CREATE TABLE statements.

## Outbound Reminder Calls

APScheduler fires every 15 min. Finds appointments 23–25h out with `reminder_sent_at IS NULL`. Triggers Twilio REST call → Twilio hits `/voice?outbound=true&appointmentId=X` on the bridge.

## AssemblyAI Tool Timing

Send `tool.result` **immediately** after receiving `tool.call` — do not wait for `reply.done`. If `reply.done.status == "interrupted"`, discard any results not yet sent.

## What NOT to Do

- Never use Notion, Supabase, or Gemini APIs — all deleted
- Never put API keys in bridge client-side code
- Never block the FastAPI async loop with synchronous SQLite calls without `run_in_executor`
- Never skip `tool.result` after a `tool.call` (even on error — return `{"error": "..."}`)
