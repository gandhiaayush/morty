# Bridge Contract

Reference for the TypeScript bridge developer. This document describes every integration point between the bridge and the rest of the Morty system.

---

## What the Bridge Must Do

The bridge is the real-time nerve center of the system. It must:

1. **Accept Twilio media stream WebSockets** — receive and send μ-law audio from/to the PSTN caller.
2. **Open and manage AssemblyAI Voice Agent WebSockets** — one session per active call.
3. **No audio conversion needed** — configure both Twilio and AssemblyAI to use `audio/pcmu` (μ-law 8kHz). Twilio G.711 μ-law is byte-compatible with AssemblyAI `audio/pcmu` — forward base64 payloads as-is.
4. **Dispatch tool calls** — when AssemblyAI emits `tool.call`, POST to the tool-server and **immediately** return `tool.result`.
5. **Handle barge-in** — on `input.speech.started`, send Twilio `clear` event to stop audio playback.
6. **Handle caller hang-up** — on Twilio `stop` event, close the AssemblyAI WebSocket.
7. **Handle reconnects** — on WebSocket drop, attempt `session.resume` within 30 seconds with a fresh token.

---

## AssemblyAI WebSocket Connection

### URL (Twilio integration — confirmed from live docs)

```
wss://agents.assemblyai.com/v1/realtime
```

### Authentication header

```
Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31
```

The `Bearer` prefix is **required**. Omitting it causes an immediate WebSocket rejection.

### Connection example

```typescript
import WebSocket from 'ws';

const aaiWs = new WebSocket('wss://agents.assemblyai.com/v1/realtime', {
  headers: {
    Authorization: `Bearer ${process.env.ASSEMBLYAI_API_KEY}`,
  },
});
```

---

## Startup: Fetching Configuration from Tool-Server

On call connect, fetch two endpoints (no role detection — all callers get the same config).

### Step 1 — Fetch tool schemas

```
GET {TOOL_SERVER_URL}/tools/schemas
```

**Response:**

```json
{
  "tools": [
    {
      "name": "book_appointment",
      "description": "...",
      "parameters": { "type": "object", "properties": { ... }, "required": [...] }
    }
  ]
}
```

Use the `tools` array as the value of `session.tools` in `session.update`.

### Step 2 — Fetch system prompt and greeting

```
GET {TOOL_SERVER_URL}/tools/prompts
```

**Response:**

```json
{
  "system_prompt": "You are Morty, a friendly AI receptionist for a nail salon...",
  "greeting": "Hi! Thanks for calling. How can I help you today?"
}
```

---

## session.update — Construction and Timing

### Timing

Send `session.update` **on the AssemblyAI WebSocket `open` event**, before `session.ready` arrives. Do not wait.

### Correct session.update for Twilio (from live AssemblyAI docs)

```typescript
// Send immediately on aaiWs 'open' event — before session.ready
aaiWs.send(JSON.stringify({
  type: 'session.update',
  session: {
    system_prompt: prompts.system_prompt,
    greeting:      prompts.greeting,
    input: {
      type:   'audio',
      format: { encoding: 'audio/pcmu' },   // Twilio μ-law — zero conversion
      keyterms: ['Morty', 'manicure', 'pedicure', 'OPI', 'gel', 'acrylic'],
      turn_detection: {
        vad_threshold:      0.45,
        min_silence:        250,
        max_silence:        700,
        interrupt_response: true,
      },
    },
    output: {
      type:   'audio',
      voice:  'emma',                        // Lively, young, conversational (US)
      format: { encoding: 'audio/pcmu' },   // Return μ-law — Twilio needs zero conversion
    },
    tools: schemas.tools,
  },
}));
```

**Immutable after `session.ready`:** `greeting`, `output.voice`, `input.format.encoding`, `output.format.encoding`. All others can be updated mid-session with another `session.update`.

---

## Tool Dispatcher

When the bridge receives a `tool.call` event from AssemblyAI, it must:

1. Extract `call_id`, `name`, and `arguments` from the event.
2. POST to `{TOOL_SERVER_URL}/tools/{name}` with `arguments` as the JSON body.
3. Send `tool.result` **immediately** on receiving the HTTP response — do not wait for `reply.done`.

### Implementation

```typescript
aaiWs.on('message', async (raw: string) => {
  const event = JSON.parse(raw);

  if (event.type === 'tool.call') {
    const { call_id, name, arguments: args } = event;
    // arguments is already a parsed object — do NOT JSON.parse again

    let result: object;
    try {
      const response = await fetch(`${TOOL_SERVER_URL}/tools/${name}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(args),
      });
      result = await response.json();

      if (!response.ok) {
        // Tool-server returned 4xx/5xx — still send a result, never crash
        result = { error: (result as any).error ?? `Tool server error: ${response.status}` };
      }
    } catch (err) {
      // Network error — still send a result
      result = { error: 'Could not reach tool server. Please try again.' };
    }

    // SEND IMMEDIATELY — do not buffer or delay
    aaiWs.send(JSON.stringify({
      type:    'tool.result',
      call_id,
      result:  JSON.stringify(result),   // result MUST be a JSON string, not an object
    }));
  }
});
```

### Error handling rule

If the tool-server returns 4xx or 5xx — or if the network request fails entirely — always send a `tool.result` with a user-friendly error message. Never let the AssemblyAI session hang waiting for a result. Never crash the bridge process on a tool error.

---

## Twilio Audio Handling

### Recommended: Use `audio/pcmu` (no resampling)

Configure both `input.format` and `output.format` as `audio/pcmu` in `session.update`. Then:

**Inbound (Twilio → AssemblyAI):**

```typescript
twilioWs.on('message', (raw: string) => {
  const msg = JSON.parse(raw);
  if (msg.event === 'media' && msg.media.track === 'inbound') {
    aaiWs.send(JSON.stringify({
      type:  'input.audio',
      audio: msg.media.payload,   // already base64 μ-law — forward directly
    }));
  }
});
```

**Outbound (AssemblyAI → Twilio):**

```typescript
if (event.type === 'reply.audio') {
  // Field is 'data', NOT 'audio'
  twilioWs.send(JSON.stringify({
    event:     'media',
    streamSid: currentStreamSid,
    media: {
      payload: event.data,         // already base64 μ-law — forward directly
    },
  }));
}
```

### Alternative: PCM16 24kHz (with resampling)

If you must use PCM16 (e.g. for audio recording), set `input.format` and `output.format` to `audio/pcm` and add a resampling layer:

- **Inbound:** base64-decode Twilio payload → μ-law bytes → decode to PCM16 8kHz → upsample to 24kHz → base64-encode → `input.audio`.
- **Outbound:** base64-decode `reply.audio.data` → PCM16 24kHz → downsample to 8kHz → encode to μ-law → base64-encode → Twilio media payload.

Recommended libraries: `@opentelecoms/voip-codec`, `node-wav-resampler`, or a native addon like `pcm-resample`.

---

## Session Logging

### On session start (after receiving `session.ready`)

```typescript
await fetch(`${TOOL_SERVER_URL}/sessions/start`, {
  method:  'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id:  sessionId,    // from session.ready
    phone:       callerPhone,
    role:        role,
    started_at:  new Date().toISOString(),
  }),
});
```

### On session end (WebSocket close or hang_up tool)

```typescript
const endedAt = new Date().toISOString();
await fetch(`${TOOL_SERVER_URL}/sessions/end`, {
  method:  'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id:   sessionId,
    ended_at:     endedAt,
    duration_sec: Math.floor((Date.now() - sessionStartMs) / 1000),
  }),
});
```

---

## Reconnect Logic

```typescript
let sessionId: string | null = null;
let sessionStartMs: number    = 0;

aaiWs.on('message', (raw: string) => {
  const event = JSON.parse(raw);

  if (event.type === 'session.ready') {
    sessionId    = event.session_id;
    sessionStartMs = Date.now();
    logSessionStart(sessionId, callerPhone, role);
  }
  // ... other event handlers
});

aaiWs.on('close', async () => {
  if (sessionId && callIsStillActive) {
    // Attempt resume within 30 seconds
    const newWs = new WebSocket('wss://agents.assemblyai.com/v1/ws', {
      headers: { Authorization: `Bearer ${process.env.ASSEMBLYAI_API_KEY}` },
    });

    newWs.on('open', () => {
      newWs.send(JSON.stringify({
        type:       'session.resume',
        session_id: sessionId,
      }));
    });

    newWs.on('message', (raw: string) => {
      const event = JSON.parse(raw);
      if (event.type === 'session.ready') {
        // Resume successful — rewire event handlers to newWs and continue
        rewireHandlers(newWs);
      } else if (event.type === 'session.error') {
        // Resume failed (>30s elapsed or session expired) — start fresh
        startNewSession(callerPhone, role);
      }
    });
  }
});
```

**30-second rule:** `session.resume` only works within 30 seconds of the disconnect. After that, start a new session (the caller will hear the greeting again).

---

## Reply Audio Playback

```typescript
if (event.type === 'reply.audio') {
  // IMPORTANT: field is 'data', not 'audio'
  const audioPayload = event.data;

  twilioWs.send(JSON.stringify({
    event:     'media',
    streamSid: currentStreamSid,
    media: {
      payload: audioPayload,
    },
  }));
}
```

Common mistake: `event.audio` is `undefined`. The correct field is `event.data`.

---

## Interruption Handling

```typescript
if (event.type === 'reply.done' && event.status === 'interrupted') {
  // 1. Stop sending audio to Twilio immediately
  flushAudioOutputBuffer();

  // 2. Send a 'clear' message to Twilio to stop playback
  twilioWs.send(JSON.stringify({
    event:     'clear',
    streamSid: currentStreamSid,
  }));

  // 3. Discard any pending tool results for this turn
  pendingToolResults.clear();
}
```

---

## Environment Variables

Create a `.env` file in the `bridge/` directory:

```bash
# AssemblyAI
ASSEMBLYAI_API_KEY=c65d449af3f24b93b92b6a4b31e65a31

# Tool-server base URL (use ngrok URL in development)
TOOL_SERVER_URL=https://xxxx.ngrok.io

# Twilio credentials (for outbound call TwiML responses)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here

# Bridge server port
PORT=3000

# Log level: debug | info | warn | error
LOG_LEVEL=info
```

### Variable reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ASSEMBLYAI_API_KEY` | Yes | AssemblyAI API key. Used in `Authorization: Bearer` header. |
| `TOOL_SERVER_URL` | Yes | Base URL of the Python tool-server. Include protocol and port, no trailing slash. |
| `TWILIO_ACCOUNT_SID` | Yes | Twilio account SID for validating incoming webhook requests. |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio auth token for webhook signature validation. |
| `PORT` | No | Port for the bridge HTTP/WebSocket server. Default: `3000`. |
| `LOG_LEVEL` | No | Logging verbosity. Default: `info`. |

---

## Full Message Flow Summary

```
Caller dials
    │
    ▼
Twilio POST /twilio/voice
    │  bridge returns TwiML <Stream>
    ▼
Twilio opens WebSocket to /twilio/stream
    │
    ▼  bridge: GET /sessions/role?phone=...
       bridge: GET /tools/schemas?role=...
       bridge: GET /tools/prompts?role=...
    │
    ▼
bridge opens WebSocket to wss://agents.assemblyai.com/v1/ws
    │  Authorization: Bearer <key>
    ▼
bridge sends session.update  ← on 'open' event, immediately
    │
    ▼
AssemblyAI sends session.ready { session_id }
    │  bridge: POST /sessions/start
    │  bridge: saves session_id for reconnect
    ▼
Audio loop:
  Twilio media frame
    → extract payload (base64 μ-law)
    → bridge sends input.audio { audio: payload }
    → AssemblyAI processes speech
    → tool.call event → bridge POSTs /tools/{name} → sends tool.result IMMEDIATELY
    → reply.audio frames { data: base64 } → bridge forwards to Twilio
    → reply.done

Call ends (hang_up tool or Twilio disconnect):
    │  bridge: POST /sessions/end
    │  bridge: closes both WebSockets
    ▼
Done
```
