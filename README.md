# Morty — Nail Salon Voice Agent

> A phone number that thinks. Customers call to book and manage appointments. Every interaction writes directly to SQLite in real time.

---

## What It Does

One Twilio phone number handles any caller. AssemblyAI's Voice Agent API handles speech-to-text, LLM reasoning, and text-to-speech in a single real-time WebSocket. The Python tool-server executes all business logic against a local SQLite database.

| Caller | Experience |
|--------|------------|
| **Customer** | Book, modify, or cancel appointments; check service prices and nail color availability; request a callback — all by speaking naturally |
| **Owner** | Full schedule rundown, appointment status updates, callback management, manual reminder triggers — all by voice |

All callers receive the full tool set — no role split in the current implementation.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INBOUND CALL FLOW                         │
│                                                                     │
│   Caller dials Twilio number                                        │
│           │                                                         │
│           ▼                                                         │
│   ┌───────────────┐  TwiML <Stream>  ┌──────────────────────────┐  │
│   │    Twilio     │ ──WebSocket────► │   TypeScript Bridge       │  │
│   │  (PSTN/RTP)   │ ◄──μ-law 8kHz─  │   POST /twilio/voice      │  │
│   └───────────────┘                  │   WS   /twilio/stream     │  │
│                                      └────────────┬─────────────┘  │
│                                                   │ audio/pcmu     │
│                                      ┌────────────▼─────────────┐  │
│                                      │  AssemblyAI Voice Agent   │  │
│                                      │  wss://agents.assemblyai  │  │
│                                      │      .com/v1/realtime     │  │
│                                      │  STT + LLM + TTS + tools  │  │
│                                      └────────────┬─────────────┘  │
│                                                   │ tool.call HTTP │
│                                      ┌────────────▼─────────────┐  │
│                                      │  Python FastAPI           │  │
│                                      │  Tool-Server (:8000)      │  │
│                                      │  SQLite  morty.db         │  │
│                                      └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       OUTBOUND REMINDER CALLS                       │
│                                                                     │
│   APScheduler job fires every 15 min                                │
│     → finds appointments 23–25h out, reminder_sent = 0             │
│     → Twilio REST API places outbound call                          │
│     → Bridge opens AssemblyAI session with reminder greeting        │
│     → Customer can confirm, reschedule, or cancel by voice          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Call Flow (Step by Step)

```
1. Caller dials Twilio number
2. Twilio POST /twilio/voice
3. Bridge returns TwiML <Stream> → Twilio opens WS to /twilio/stream
4. Bridge fetches on startup:
   GET /tools/schemas   → tool definitions for session.update
   GET /tools/prompts   → { system_prompt, greeting }
5. Bridge opens AssemblyAI WS: wss://agents.assemblyai.com/v1/realtime
   Authorization: Bearer <ASSEMBLYAI_API_KEY>
6. On WS open, bridge sends session.update (system prompt, greeting, tools, audio/pcmu)
7. AssemblyAI sends session.ready { session_id }
8. Bridge: POST /sessions/start
9. Audio loop:
   Twilio μ-law frame → input.audio { audio: base64 } → AssemblyAI
   AssemblyAI → tool.call → bridge POSTs /tools/{name} → tool.result IMMEDIATELY
   AssemblyAI → reply.audio { data: base64 } → Twilio → caller
10. hang_up tool or caller disconnect
    → Bridge: POST /sessions/end → closes both WebSockets
```

---

## Audio Pipeline

No transcoding needed. Twilio G.711 μ-law is byte-compatible with AssemblyAI `audio/pcmu`.

| Direction | Format | Action |
|-----------|--------|--------|
| Twilio → Bridge | μ-law 8kHz base64 | Extract `media.payload`, forward as-is |
| Bridge → AssemblyAI | `input.audio { audio: payload }` | Forward base64 directly |
| AssemblyAI → Bridge | `reply.audio { data: base64 }` | Note: field is `data`, not `audio` |
| Bridge → Twilio | μ-law 8kHz base64 | Wrap in `{ event: "media", media: { payload } }` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Phone / PSTN | Twilio Voice — `<Connect><Stream>` WebSocket |
| Voice Agent | AssemblyAI Voice Agent API (`wss://agents.assemblyai.com/v1/realtime`) |
| Bridge | TypeScript + Express + `ws` |
| Tool Server | Python 3.11+ + FastAPI + `uvicorn` |
| Database | SQLite (`morty.db`) — no external DB |
| Scheduler | APScheduler — automated reminder calls |

---

## Project Structure

```
morty/
├── tool-server/              # Python FastAPI + SQLite
│   ├── main.py               # FastAPI app entry point, lifespan, router registration
│   ├── database.py           # SQLite connection + get_db dependency
│   ├── models.py             # SQLAlchemy-style models (if present)
│   ├── schemas.py            # /tools/schemas and /tools/prompts endpoints
│   ├── prompts.py            # CONSUMER_SYSTEM, CONSUMER_GREETING strings
│   ├── scheduler.py          # APScheduler reminder job
│   ├── seed.py               # seed_if_empty() — seeds DB on first run
│   └── tools/
│       ├── customers.py      # normalize_phone(), upsert_customer() helpers
│       ├── crud.py           # book/modify/cancel/update_status/append_note
│       ├── search.py         # search_customer, get_appointment, list_available_slots,
│       │                     # list_today_appointments
│       ├── services.py       # list_services, check_service, check_inventory
│       └── callbacks.py      # request_callback, list_pending_callbacks,
│                             # resolve_callback, hang_up
│
├── bridge/                   # TypeScript Twilio ↔ AssemblyAI (partner builds)
│   ├── server.ts
│   ├── twilio.ts
│   ├── assemblyai.ts
│   └── tool-dispatcher.ts
│
├── ARCHITECTURE.md           # Full system diagram + session lifecycle sequence diagram
├── BRIDGE_CONTRACT.md        # Bridge integration spec (AssemblyAI WS, tool dispatch, audio)
├── SCHEMA.md                 # SQLite schema reference
└── ASSEMBLYAI.md             # AssemblyAI WebSocket API reference + gotchas
```

---

## Tool-Server: Run

```bash
cd morty/tool-server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On startup: `init_db()` → `seed_if_empty()` → `start_scheduler()` (APScheduler reminder job).

---

## Tool-Server: Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tools/schemas` | AssemblyAI tool definitions — bridge calls on startup |
| `GET` | `/tools/prompts` | Returns `{ system_prompt, greeting }` — bridge calls on startup |
| `POST` | `/tools/{tool_name}` | Execute any tool with JSON body |
| `POST` | `/sessions/start` | Log session open `{ session_id, phone, role, started_at }` |
| `POST` | `/sessions/end` | Log session close `{ session_id, ended_at, duration_sec }` |
| `GET` | `/health` | Returns `{ status: "ok" }` |

---

## Tools

All callers receive all tools. No role filtering.

### Booking & Appointment Management

| Tool | Endpoint | Key Args |
|------|----------|----------|
| `search_customer` | `POST /tools/search_customer` | `phone?`, `name?` |
| `get_appointment` | `POST /tools/get_appointment` | `appointment_id` |
| `list_available_slots` | `POST /tools/list_available_slots` | `date` (YYYY-MM-DD), `service_name?` |
| `book_appointment` | `POST /tools/book_appointment` | `name`, `phone`, `service`, `datetime`, `color?` |
| `modify_appointment` | `POST /tools/modify_appointment` | `appointment_id`, `datetime?`, `service?`, `color?` |
| `cancel_appointment` | `POST /tools/cancel_appointment` | `appointment_id` |

### Services & Inventory

| Tool | Endpoint | Key Args |
|------|----------|----------|
| `list_services` | `POST /tools/list_services` | *(none)* |
| `check_service` | `POST /tools/check_service` | `service_name` |
| `check_inventory` | `POST /tools/check_inventory` | `color_name` |

### Owner / Operations

| Tool | Endpoint | Key Args |
|------|----------|----------|
| `list_today_appointments` | `POST /tools/list_today_appointments` | *(none)* |
| `update_appointment_status` | `POST /tools/update_appointment_status` | `appointment_id`, `status` |
| `list_pending_callbacks` | `POST /tools/list_pending_callbacks` | *(none)* |
| `resolve_callback` | `POST /tools/resolve_callback` | `callback_id`, `status` |
| `trigger_reminder_call` | `POST /tools/trigger_reminder_call` | `appointment_id` |
| `append_appointment_note` | `POST /tools/append_appointment_note` | `appointment_id`, `note` |

### Call Control

| Tool | Endpoint | Key Args |
|------|----------|----------|
| `request_callback` | `POST /tools/request_callback` | `name`, `phone`, `reason` |
| `hang_up` | `POST /tools/hang_up` | *(none)* — bridge handles actual hangup |

---

## SQLite Schema (actual columns from code)

### `services`
`id`, `name`, `category`, `price_cents` (integer, USD cents), `duration_minutes`, `description`, `available`

### `inventory`
`id`, `color_name`, `brand`, `in_stock` (boolean 0/1)

### `appointments`
`id`, `customer_id` (FK), `service_id` (FK), `nail_color`, `datetime` (ISO 8601), `status`, `notes`, `call_sid`, `reminder_sent` (boolean 0/1), `created_at`

Valid statuses: `Pending`, `Confirmed`, `Completed`, `Cancelled`, `No-Show`

### `customers`
`id`, `name`, `phone` (E.164, unique), `created_at`

### `callbacks`
`id`, `customer_id` (FK, nullable), `phone`, `reason`, `status` (`Pending` / `Called` / `Resolved`), `attempts`, `created_at`, `resolved_at`

### `sessions`
`id`, `session_id` (AssemblyAI session_id, unique), `phone`, `role`, `started_at`, `ended_at`, `duration_sec`

See [morty/SCHEMA.md](morty/SCHEMA.md) for full `CREATE TABLE` statements.

---

## Environment Variables

### tool-server (`morty/tool-server/.env`)

```bash
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
TWILIO_WEBHOOK_BASE=         # bridge public URL, no trailing slash
OWNER_PHONE_NUMBER=
DB_PATH=morty.db
PORT=8000
```

### bridge (`morty/bridge/.env`)

```bash
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TOOL_SERVER_URL=http://localhost:8000   # or ngrok URL in dev
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
PORT=3000
LOG_LEVEL=info
```

---

## Dev Setup

```bash
# Start tool-server (seeds DB automatically on first run)
cd morty/tool-server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Expose bridge publicly for Twilio webhooks
ngrok http 3000

# Start bridge (partner repo)
cd morty/bridge
npm install
npm run dev
```

Set `TWILIO_WEBHOOK_BASE` to the ngrok URL. Point Twilio voice webhook at `https://{ngrok}/twilio/voice`.

---

## Outbound Reminder Calls

APScheduler fires every 15 minutes inside the tool-server:

```
Find: appointments WHERE datetime BETWEEN now+23h AND now+25h
      AND reminder_sent = 0 AND status IN ('Pending', 'Confirmed')

For each match:
  → Twilio REST API places outbound call to customer
  → Twilio hits bridge /twilio/reminder?appointment_id={id}
  → Bridge opens AssemblyAI session with reminder greeting
  → Customer confirms, reschedules, or cancels by voice
  → tool-server sets reminder_sent = 1
```

---

## AssemblyAI: Critical Rules

| # | Rule |
|---|------|
| 1 | Send `tool.result` **immediately** after receiving `tool.call` — never wait for `reply.done` |
| 2 | `reply.audio` audio payload is in **`data`** field, not `audio` |
| 3 | `tool.result.result` must be **`JSON.stringify(obj)`** — a string, not an object |
| 4 | `tool.call.arguments` is already a parsed object — do not `JSON.parse` again |
| 5 | Send `session.update` on WebSocket `open` event — before `session.ready` arrives |
| 6 | `Authorization: Bearer <key>` — the `Bearer` prefix is required |
| 7 | `session.resume` only works within **30 seconds** of disconnect |
| 8 | On `reply.done.status == "interrupted"` — flush Twilio output buffer and discard pending tool results |

See [morty/ASSEMBLYAI.md](morty/ASSEMBLYAI.md) for the full API reference.
