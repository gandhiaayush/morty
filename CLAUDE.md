# morty — Nail Salon Voice Agent

## Project Overview

Voice agent for nail salon booking. Twilio handles PSTN. AssemblyAI Voice Agent API handles STT + LLM + TTS. Python FastAPI tool-server handles all business logic. SQLite is the only database.

**Status (2026-05-19):** Full stack built and confirmed working. Bridge + tool-server both run locally with ngrok tunnel.

## Repository Layout

```
untitled folder copy/
├── morty/
│   ├── tool-server/      # Python FastAPI + SQLite — DONE
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
│   └── bridge/           # TypeScript Twilio ↔ AssemblyAI — DONE
│       └── server.ts     # single file, runs from project root
└── src/                  # OLD STACK — do not touch, scheduled for deletion
```

## Stack

| Layer | Tech |
|-------|------|
| Phone/PSTN | Twilio Voice (+19255155725) |
| Voice Agent | AssemblyAI Voice Agent API (`wss://agents.assemblyai.com/v1/realtime`) |
| Bridge | TypeScript + Express + ws (port 3001) |
| Tool Server | Python 3.11+ + FastAPI (port 8000) |
| Database | SQLite (`morty.db`) |
| Scheduler | APScheduler (reminder calls every 15 min) |

## How to Run (3 terminals)

**Terminal 1 — tool-server:**
```bash
cd "/Users/dhruvavutukury/untitled folder copy/morty/tool-server"
uvicorn main:app --reload --port 8000
```

**Terminal 2 — bridge:**
```bash
cd "/Users/dhruvavutukury/untitled folder copy"
npx tsx morty/bridge/server.ts
```

**Terminal 3 — ngrok:**
```bash
ngrok http 3001
```

Then in Twilio console → +19255155725 → Voice webhook → `https://<ngrok-url>/voice` (HTTP POST).

**Port conflicts** (common): `lsof -ti :8000 | xargs kill -9` and `lsof -ti :3001 | xargs kill -9`

## Tool-Server: Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools/schemas` | All AssemblyAI tool definitions (no role param — all callers get everything) |
| GET | `/tools/prompts` | System prompt + greeting for session.update |
| POST | `/tools/{tool_name}` | Execute any tool with JSON body |
| GET | `/health` | Health check |

## Tool-Server: All Tools

### Consumer (11)
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

All callers receive all 17 tools (no role distinction enforced at schema level).

## Bridge → Tool-Server HTTP Contract

```
POST http://localhost:8000/tools/{tool_name}
Content-Type: application/json
{ ...tool_arguments }   ← from tool.call.arguments (already parsed object)

→ 200: { ...result }    ← bridge JSON.stringify() this for tool.result.result
→ 4xx/5xx: { "error": "..." }
```

Bridge fetches on Twilio connect:
```
GET http://localhost:8000/tools/schemas  → { tools: [...] }
GET http://localhost:8000/tools/prompts  → { system_prompt, greeting }
```

## AssemblyAI Session Config

```typescript
{
  type: 'session.update',
  session: {
    system_prompt: prompts.system_prompt,
    greeting: prompts.greeting,
    input: {
      type: 'audio',
      format: { encoding: 'audio/pcmu' },   // Twilio μ-law — zero conversion
      turn_detection: { vad_threshold: 0.45, min_silence: 250, max_silence: 700, interrupt_response: true },
    },
    output: {
      type: 'audio',
      voice: 'emma',
      format: { encoding: 'audio/pcmu' },
    },
    tools: schemas.tools,
  }
}
```

Key gotchas:
- WS URL: `wss://agents.assemblyai.com/v1/realtime` (not /ws)
- Auth: `Authorization: Bearer <key>` — Bearer prefix required
- `reply.audio` data is in `event.data` field (NOT `event.audio`)
- Send `tool.result` IMMEDIATELY after `tool.call` — don't wait for `reply.done`
- Barge-in: send Twilio `clear` event on `input.speech.started`

## AssemblyAI Auth

```
Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31
```

## Environment Variables

### tool-server/.env (gitignored — recreate manually)
```
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TWILIO_ACCOUNT_SID=<your-twilio-account-sid>
TWILIO_AUTH_TOKEN=67cb603bfadce0da4e87b24b8c2ef88e
TWILIO_PHONE_NUMBER=+19255155725
OWNER_PHONE_NUMBER=
TWILIO_WEBHOOK_BASE=https://<ngrok-url>
WEBHOOK_BASE=https://<ngrok-url>
DB_PATH=morty.db
PORT=8000
```

### bridge/.env (gitignored — recreate manually)
```
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TWILIO_ACCOUNT_SID=<your-twilio-account-sid>
TWILIO_AUTH_TOKEN=67cb603bfadce0da4e87b24b8c2ef88e
TWILIO_PHONE_NUMBER=+19255155725
WEBHOOK_BASE=https://<ngrok-url>
TOOL_SERVER_URL=http://localhost:8000
PORT=3001
```

Update `WEBHOOK_BASE` every time ngrok restarts.

## SQLite Tables

`customers`, `services`, `inventory`, `appointments`, `callbacks`, `sessions`

See `morty/SCHEMA.md` for full CREATE TABLE statements.

## Outbound Reminder Calls

APScheduler fires every 15 min. Finds appointments 23–25h out with `reminder_sent_at IS NULL`. Triggers Twilio REST call → Twilio hits `/voice?outbound=true&appointmentId=X` on the bridge.

## What NOT to Do

- Never use Notion, Supabase, or Gemini APIs — all deleted
- Never push to any repo except `gandhiaayush/morty` branch `voice-agent`
- Never put API keys in committed code
- Never skip `tool.result` after a `tool.call` (even on error — return `{"error": "..."}`)
- Never block FastAPI async loop with synchronous SQLite calls without `run_in_executor`
