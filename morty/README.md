# Morty — Nail Salon Voice Agent

Morty is an AI-powered phone receptionist for a nail salon. Incoming calls land on a Twilio phone number, which streams audio to a TypeScript bridge. The bridge opens a WebSocket to AssemblyAI's Voice Agent API, receives turn-by-turn transcripts, dispatches tool calls to a Python FastAPI tool-server, and plays agent audio back to the caller — all in real time. A built-in APScheduler inside the tool-server fires outbound reminder calls 24 hours before each appointment.

---

## Architecture

```
                         ┌─────────────────────────────────────────────────────┐
                         │                  TypeScript Bridge                  │
                         │                                                     │
  PSTN ──► Twilio ──► WebSocket (media stream)                                 │
                         │   ┌─────────────────┐   HTTP tool dispatch          │
                         │   │  Audio adapter  │──► POST /tools/{name}         │
                         │   │ μ-law ↔ PCM16   │                               │
                         │   └────────┬────────┘   ◄── JSON response           │
                         │            │                                         │
                         │   WebSocket (wss://agents.assemblyai.com/v1/ws)     │
                         └────────────┼────────────────────────────────────────┘
                                      │
                              AssemblyAI Voice
                               Agent API (cloud)
                                      │
                         ┌────────────┼────────────────────────────────────────┐
                         │            │      Python FastAPI Tool-Server        │
                         │   POST /tools/{name}                                │
                         │            │                                         │
                         │   ┌────────▼────────┐   ┌──────────────────────┐   │
                         │   │  Business Logic  │──►│  SQLite (morty.db)   │   │
                         │   └─────────────────┘   └──────────────────────┘   │
                         │            │                                         │
                         │   APScheduler (reminder jobs)                        │
                         └─────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Minimum version |
|-------------|----------------|
| Python | 3.11+ |
| Node.js | 18+ |
| ngrok (or equivalent tunnel) | Latest |
| Twilio account | — |
| AssemblyAI account | — |

---

## Setup

### 1. Tool-Server (Python / FastAPI)

```bash
cd morty/tool-server

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env — see variables table below

# Start the server (development)
uvicorn main:app --reload --port 8000
```

Verify it's alive:

```bash
curl http://localhost:8000/health
```

### 2. Bridge (TypeScript)

```bash
cd morty/bridge

# Install dependencies
npm install

# Create environment file
cp .env.example .env
# Edit .env — see bridge env vars in bridge/BRIDGE_CONTRACT.md

# Start in development mode
npm run dev
```

### 3. Expose tool-server via tunnel

```bash
ngrok http 8000
# Copy the https URL → TOOL_SERVER_URL in bridge .env
```

### 4. Configure Twilio

Point your Twilio phone number's **A call comes in** webhook to:

```
https://<your-bridge-ngrok-url>/twilio/voice
```

---

## Tool-Server Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Path to SQLite file, e.g. `./morty.db` |
| `ASSEMBLYAI_API_KEY` | Yes | — | `c65d449af3f24b93b92b6a4b31e65a31` |
| `TWILIO_ACCOUNT_SID` | Yes | — | Twilio account SID for outbound calls |
| `TWILIO_AUTH_TOKEN` | Yes | — | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Yes | — | Twilio phone number in E.164 format |
| `OWNER_PHONE` | Yes | — | Salon owner's phone number in E.164 |
| `REMINDER_HOURS_BEFORE` | No | `24` | Hours before appointment to send reminder |
| `PORT` | No | `8000` | uvicorn bind port |
| `LOG_LEVEL` | No | `info` | Logging verbosity |

---

## Quick Test Commands

### Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "ok", "timestamp": "2026-05-19T12:00:00Z" }
```

### List services

```bash
curl -X POST http://localhost:8000/tools/list_services \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response:

```json
{
  "services": [
    { "id": 1, "name": "Classic Manicure", "price": 25.00, "duration_min": 30, "description": "Basic nail shaping and polish" },
    { "id": 2, "name": "Gel Manicure", "price": 45.00, "duration_min": 45, "description": "Long-lasting gel polish" }
  ]
}
```

### Book an appointment

```bash
curl -X POST http://localhost:8000/tools/book_appointment \
  -H "Content-Type: application/json" \
  -d '{
    "customer_phone": "+15551234567",
    "customer_name": "Jane Smith",
    "service_id": 1,
    "datetime": "2026-05-21T14:00:00",
    "technician": "Any"
  }'
```

Expected response:

```json
{
  "success": true,
  "appointment_id": 42,
  "confirmation": "Appointment booked for Jane Smith on Wednesday May 21 at 2:00 PM for Classic Manicure."
}
```

---

## Outbound Reminder Calls

The tool-server runs an **APScheduler** background job that:

1. Queries the `appointments` table every hour for appointments where `datetime` is between `now + REMINDER_HOURS_BEFORE` and `now + REMINDER_HOURS_BEFORE + 1h` and `reminder_sent = 0`.
2. For each match, places an outbound call via the Twilio REST API using `TWILIO_FROM_NUMBER`.
3. The call webhook URL points back to the bridge, which opens a new AssemblyAI Voice Agent session configured with the **reminder prompt** (fetched from `GET /tools/prompts?role=consumer`).
4. After the call completes, the scheduler sets `reminder_sent = 1` on the appointment row.

To manually trigger a reminder for a specific appointment:

```bash
curl -X POST http://localhost:8000/tools/trigger_reminder_call \
  -H "Content-Type: application/json" \
  -d '{ "appointment_id": 42 }'
```
