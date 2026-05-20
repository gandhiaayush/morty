# Morty Architecture

## System Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                               PSTN / Caller                                   │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ phone call
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              Twilio                                           │
│                                                                               │
│  • Receives inbound PSTN call                                                 │
│  • Returns TwiML that opens a <Stream> WebSocket to the bridge                │
│  • Encodes audio as μ-law 8 kHz (PCMU), base64-encoded JSON frames            │
│  • Places outbound calls when tool-server triggers a reminder                 │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ WebSocket (μ-law 8kHz media stream)
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         TypeScript Bridge                                     │
│                                                                               │
│  ┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐  │
│  │  Twilio WS handler  │    │    Audio adapter      │    │ Tool dispatcher │  │
│  │                     │───►│  μ-law → PCM16 24kHz  │    │                 │  │
│  │  • Parse media msgs │    │  (or skip if pcmu out)│    │ on tool.call:   │  │
│  │  • Write reply audio│◄───│  PCM16 → μ-law        │    │ POST /tools/    │  │
│  │  • Handle hangup    │    └──────────┬───────────┘    │  {name}         │  │
│  └─────────────────────┘               │                └────────┬────────┘  │
│                                        │ input.audio events      │           │
│                                        ▼                         │           │
│                         ┌──────────────────────────┐             │           │
│                         │  AssemblyAI Voice Agent   │             │           │
│                         │       WebSocket           │◄────────────┘           │
│                         │  wss://agents.assemblyai  │  tool.result events     │
│                         │      .com/v1/ws           │                         │
│                         └──────────────────────────┘                         │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ HTTP (tool dispatch)
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    Python FastAPI Tool-Server (:8000)                         │
│                                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────────┐    │
│  │  /tools/{name}  │  │  /sessions/*     │  │  APScheduler              │    │
│  │                 │  │  /tools/schemas  │  │                           │    │
│  │  business logic │  │  /tools/prompts  │  │  hourly reminder job      │    │
│  │  reads/writes   │  │  /health         │  │  → Twilio outbound call   │    │
│  └────────┬────────┘  └──────────────────┘  └───────────────────────────┘    │
│           │                                                                   │
│           ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         SQLite  (morty.db)                              │ │
│  │  customers │ services │ inventory │ appointments │ callbacks │ sessions  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Session Lifecycle

```
Bridge                          AssemblyAI                     Tool-Server
  │                                  │                               │
  │── WebSocket connect ────────────►│                               │
  │                                  │                               │
  │── session.update ───────────────►│  (send immediately on open)  │
  │   { system_prompt, greeting,     │                               │
  │     input, output, tools }       │                               │
  │                                  │                               │
  │◄─ session.ready ────────────────│  { session_id }               │
  │   (log session_id)               │                               │
  │── POST /sessions/start ─────────────────────────────────────────►│
  │                                  │                               │
  │── input.audio (loop) ──────────►│                               │
  │                                  │                               │
  │◄─ input.speech.started ─────────│                               │
  │◄─ input.speech.stopped ─────────│                               │
  │◄─ transcript.user.delta ────────│  (streaming partial)          │
  │◄─ transcript.user ──────────────│  (final user turn text)       │
  │◄─ reply.started ────────────────│                               │
  │                                  │                               │
  │◄─ tool.call ────────────────────│  { call_id, name, arguments } │
  │── POST /tools/{name} ───────────────────────────────────────────►│
  │◄─ HTTP 200 { ... } ─────────────────────────────────────────────│
  │── tool.result ─────────────────►│  SEND IMMEDIATELY             │
  │   { call_id, result }            │                               │
  │                                  │                               │
  │◄─ reply.audio (loop) ───────────│  { data: base64 }             │
  │◄─ transcript.agent ─────────────│  (agent turn text)            │
  │◄─ reply.done ───────────────────│  { status: "success" }        │
  │                                  │                               │
  │  ... (conversation continues) ...│                               │
  │                                  │                               │
  │  WebSocket close / hang_up tool  │                               │
  │── POST /sessions/end ───────────────────────────────────────────►│
```

### Key timing rule

`tool.result` MUST be sent **immediately** after receiving `tool.call` — do not wait for `reply.done`. AssemblyAI holds the agent's response pipeline open waiting for results; any delay causes audible silence or timeouts.

---

## Bridge ↔ Tool-Server HTTP Contract

All requests use `Content-Type: application/json`. All responses return HTTP 200 with a JSON body on success, or HTTP 4xx/5xx with `{ "error": "<message>" }` on failure.

### Startup / configuration endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/tools/schemas?role={role}` | Returns AssemblyAI-formatted tool schema array for the given role (`consumer` or `owner`) |
| `GET` | `/tools/prompts?role={role}` | Returns `{ system_prompt, greeting }` strings for the given role |
| `GET` | `/sessions/role?phone={phone}` | Returns `{ role: "consumer" \| "owner" }` based on caller phone number |
| `GET` | `/health` | Returns `{ status: "ok" }` |

### Tool dispatch endpoints

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| `POST` | `/tools/{tool_name}` | Tool arguments as flat JSON object | Execute a tool; returns tool-specific JSON |

### Session audit endpoints

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| `POST` | `/sessions/start` | `{ session_id, phone, role, started_at }` | Log session open |
| `POST` | `/sessions/end` | `{ session_id, ended_at, duration_sec }` | Log session close |

### Schema endpoint response format

```json
{
  "tools": [
    {
      "name": "book_appointment",
      "description": "Book a nail appointment for the caller.",
      "parameters": {
        "type": "object",
        "properties": {
          "customer_name": { "type": "string", "description": "Full name of the customer" },
          "service_id":    { "type": "integer", "description": "ID of the service from list_services" },
          "datetime":      { "type": "string", "description": "ISO 8601 datetime for the appointment" }
        },
        "required": ["customer_name", "service_id", "datetime"]
      }
    }
  ]
}
```

### Prompts endpoint response format

```json
{
  "system_prompt": "You are Morty, a friendly AI receptionist for a nail salon...",
  "greeting": "Hi! Thanks for calling. How can I help you today?"
}
```

### Role endpoint response format

```json
{ "role": "consumer" }
```

---

## Inbound Call Flow (Step by Step)

1. Caller dials the Twilio number.
2. Twilio sends an HTTP POST webhook to the bridge's `/twilio/voice` endpoint.
3. Bridge responds with TwiML instructing Twilio to open a `<Stream>` WebSocket back to `/twilio/stream`.
4. Bridge looks up the caller's `From` number: `GET /sessions/role?phone={from}`.
5. Bridge fetches `GET /tools/schemas?role={role}` and `GET /tools/prompts?role={role}`.
6. Bridge opens WebSocket to `wss://agents.assemblyai.com/v1/ws` with `Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31`.
7. Immediately on WebSocket open, bridge sends `session.update` with system prompt, greeting, audio formats, and tools array.
8. AssemblyAI responds with `session.ready { session_id }`.
9. Bridge logs `POST /sessions/start` to tool-server.
10. Bridge saves `session_id` for potential reconnect.
11. Twilio media frames arrive; bridge decodes base64 μ-law, resamples to PCM16 24kHz (or uses `audio/pcmu` input format to skip resampling), and forwards as `input.audio` events.
12. AssemblyAI detects speech, emits `input.speech.started`, `input.speech.stopped`, transcript deltas, then `transcript.user`.
13. Agent formulates a response; for tool calls, emits `tool.call`.
14. Bridge dispatches `POST /tools/{name}` to tool-server and immediately sends `tool.result`.
15. AssemblyAI streams `reply.audio` frames (base64 PCM16 or μ-law depending on `output.format`).
16. Bridge encodes reply audio back to μ-law if needed, wraps in Twilio media JSON, sends to Twilio WebSocket.
17. Caller hears agent response. Conversation loops at step 11.
18. On hang_up tool or caller disconnect, bridge logs `POST /sessions/end` and closes both WebSockets.

---

## Outbound Reminder Call Flow (Step by Step)

1. APScheduler job runs every hour inside the tool-server.
2. Query: `SELECT * FROM appointments WHERE datetime BETWEEN now+23h AND now+25h AND reminder_sent=0 AND status='confirmed'`.
3. For each result, call Twilio REST API: `POST /2010-04-01/Accounts/{SID}/Calls` with `To={customer_phone}`, `From={TWILIO_FROM_NUMBER}`, `Url={bridge_url}/twilio/reminder?appointment_id={id}`.
4. Twilio places the outbound call; on answer, calls the bridge's `/twilio/reminder` endpoint.
5. Bridge responds with TwiML opening a `<Stream>` WebSocket to `/twilio/stream?mode=reminder&appointment_id={id}`.
6. Bridge fetches reminder prompt (a specialized consumer prompt that opens with the appointment details).
7. Bridge opens AssemblyAI session exactly as in the inbound flow, with a tailored greeting like: "Hi, this is Morty calling from the nail salon. I'm reminding you about your appointment tomorrow at 2 PM..."
8. Caller can confirm, reschedule, or cancel via voice; tool calls execute normally.
9. After call ends, tool-server sets `reminder_sent=1` on the appointment row.

---

## Audio Format

### Default (with resampling in bridge)

| Direction | Format | Encoding | Sample Rate |
|-----------|--------|----------|-------------|
| Twilio → bridge | μ-law (PCMU) | base64 JSON | 8 kHz |
| bridge → AssemblyAI | PCM16 | base64 | 24 kHz |
| AssemblyAI → bridge | PCM16 | base64 | 24 kHz |
| bridge → Twilio | μ-law (PCMU) | base64 JSON | 8 kHz |

### Optimized (skip resampling — recommended)

Set `output.format` to `audio/pcmu` in `session.update`. AssemblyAI will deliver `reply.audio` already in μ-law 8kHz, which can be forwarded to Twilio with zero conversion.

```json
{
  "type": "session.update",
  "session": {
    "input":  { "format": "audio/pcmu" },
    "output": { "format": "audio/pcmu" }
  }
}
```

---

## Role Detection

The bridge calls `GET /sessions/role?phone={phone}` before opening the AssemblyAI session. The tool-server compares the caller's phone number against `OWNER_PHONE` in its environment:

- If match → `{ "role": "owner" }`
- Otherwise → `{ "role": "consumer" }`

The returned role determines which tool schemas and system prompt are loaded into the session, restricting owner-only tools from consumer sessions.

---

## Session Storage in SQLite

The `sessions` table in `morty.db` stores every call for audit and analytics:

```
sessions
  id            INTEGER PRIMARY KEY
  session_id    TEXT UNIQUE        ← AssemblyAI session_id from session.ready
  phone         TEXT               ← caller E.164
  role          TEXT               ← 'consumer' | 'owner'
  started_at    TEXT               ← ISO 8601
  ended_at      TEXT               ← ISO 8601 (nullable until call ends)
  duration_sec  INTEGER            ← computed on session end
```

Bridge writes to this table via `POST /sessions/start` and `POST /sessions/end`. See full schema in [SCHEMA.md](./SCHEMA.md).