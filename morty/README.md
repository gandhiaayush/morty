# Morty — Nail Salon Voice Agent

AI-powered phone receptionist for a nail salon. Callers hit a Twilio number, audio streams to a TypeScript bridge, which opens an AssemblyAI Voice Agent session — all speech recognition, LLM turns, and TTS handled by AssemblyAI. Tool calls dispatch to a Python FastAPI tool-server backed by SQLite. APScheduler fires outbound reminder calls 24h before appointments.

**Status:** Full stack built and working. Call +19255155725 to test.

---

## Architecture

```
Twilio (+19255155725)
    │ μ-law 8kHz audio
    ▼
[morty/bridge/server.ts]  Express + WS  port 3001
    │ wss://agents.assemblyai.com/v1/realtime
    ▼
AssemblyAI Voice Agent API (cloud)
    │ tool.call events
    ▼
[morty/tool-server/main.py]  FastAPI  port 8000
    │
    └── SQLite morty.db
```

No audio conversion — Twilio G.711 μ-law is byte-compatible with AssemblyAI `audio/pcmu`.

---

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 18+ (node_modules already in project root)
- ngrok

### Step 1 — Tool-server

```bash
cd morty/tool-server
pip install -r requirements.txt   # first time only

# Create .env (gitignored — see values below)
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

### Step 2 — Bridge

```bash
# From project root (untitled folder copy/)
npx tsx morty/bridge/server.ts
```

Create `morty/bridge/.env` (gitignored — see values below).

### Step 3 — ngrok

```bash
ngrok http 3001
```

Copy the `https://xxxx.ngrok-free.app` URL.

### Step 4 — Twilio webhook

Twilio console → Phone Numbers → +19255155725 → Voice Configuration:
- **A call comes in** → `https://<ngrok-url>/voice` (HTTP POST)

Update `WEBHOOK_BASE` in both .env files whenever ngrok restarts.

### Troubleshooting port conflicts

```bash
lsof -ti :8000 | xargs kill -9
lsof -ti :3001 | xargs kill -9
```

---

## Environment Variables

### morty/tool-server/.env

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

### morty/bridge/.env

```
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31
TWILIO_ACCOUNT_SID=<your-twilio-account-sid>
TWILIO_AUTH_TOKEN=67cb603bfadce0da4e87b24b8c2ef88e
TWILIO_PHONE_NUMBER=+19255155725
WEBHOOK_BASE=https://<ngrok-url>
TOOL_SERVER_URL=http://localhost:8000
PORT=3001
```

---

## Quick Test

```bash
# Health
curl http://localhost:8000/health

# List services
curl -X POST http://localhost:8000/tools/list_services \
  -H "Content-Type: application/json" -d '{}'

# Get tool schemas (what AssemblyAI sees)
curl http://localhost:8000/tools/schemas

# Book an appointment
curl -X POST http://localhost:8000/tools/book_appointment \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Smith","phone":"+15551234567","service":"Gel Manicure","datetime":"2026-05-21T14:00:00"}'
```

---

## Tools

### All callers get all 17 tools (no role distinction)

**Booking flow:** `search_customer` → `list_available_slots` → `check_inventory` → `book_appointment`

| Tool | Description |
|------|-------------|
| `search_customer` | Lookup by phone or name |
| `get_appointment` | Fetch by ID |
| `list_services` | All services + prices |
| `check_service` | Single service details |
| `check_inventory` | Color in stock? |
| `list_available_slots` | Open slots for a date |
| `book_appointment` | Create appointment |
| `modify_appointment` | Change datetime/service/color |
| `cancel_appointment` | Cancel by ID |
| `request_callback` | Log callback for staff |
| `hang_up` | End call cleanly |
| `list_today_appointments` | Today's schedule |
| `update_appointment_status` | Set Pending/Confirmed/Completed/Cancelled/No-Show |
| `list_pending_callbacks` | Unresolved callback requests |
| `resolve_callback` | Mark callback Called/Resolved |
| `trigger_reminder_call` | Manually fire outbound reminder |
| `append_appointment_note` | Add timestamped note |

---

## Outbound Reminders

APScheduler (inside tool-server) fires every 15 min. Finds appointments 23–25h out with `reminder_sent_at IS NULL` and status not Cancelled. Places Twilio outbound call → bridge opens AssemblyAI session with reminder prompt.

Manual trigger: `curl -X POST http://localhost:8000/tools/trigger_reminder_call -d '{"appointment_id":1}'`

---

## Key Technical Decisions

| Decision | Why |
|----------|-----|
| `audio/pcmu` both directions | Zero transcoding — Twilio μ-law is byte-compatible |
| `tool.result` sent immediately | Live AssemblyAI docs say don't wait for `reply.done` |
| `reply.audio` uses `event.data` field | Not `event.audio` — common mistake |
| WS URL ends in `/realtime` | Not `/ws` — confirmed from live Twilio integration docs |
| Single `server.ts` bridge | No need for separate files; keeps it simple |
| No role detection | All callers get same tools; simplifies bridge startup |
