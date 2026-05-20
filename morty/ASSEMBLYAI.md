# AssemblyAI Voice Agent API Reference

Complete reference for the AssemblyAI Voice Agent WebSocket API as used by Morty.

---

## WebSocket Endpoint

```
wss://agents.assemblyai.com/v1/ws
```

### Authentication

Pass the API key as a `Bearer` token in the HTTP `Authorization` header when opening the WebSocket connection. The `Bearer` prefix is **required** — omitting it causes an immediate authentication error.

```
Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31
```

**Node.js / TypeScript example:**

```typescript
import WebSocket from 'ws';

const ws = new WebSocket('wss://agents.assemblyai.com/v1/ws', {
  headers: {
    Authorization: 'Bearer c65d449af3f24b93b92b6a4b31e65a31',
  },
});
```

---

## Token Minting (Browser / Mobile)

For browser or mobile clients where the API key cannot be embedded in client-side code, mint a short-lived token server-side and pass it to the client.

**Mint a token (server-side):**

```bash
curl -X POST https://api.assemblyai.com/v1/realtime/token \
  -H "Authorization: Bearer c65d449af3f24b93b92b6a4b31e65a31" \
  -H "Content-Type: application/json" \
  -d '{ "expires_in": 3600 }'
```

**Response:**

```json
{ "token": "<short-lived-token>" }
```

**Client-side connection using token:**

```
wss://agents.assemblyai.com/v1/ws?token=<short-lived-token>
```

No `Authorization` header needed when using the `token` query parameter.

---

## `session.update` — Full Schema

Send `session.update` **immediately after the WebSocket connection is opened**, before `session.ready` arrives. Fields marked *(immutable)* cannot be changed after `session.ready`.

```json
{
  "type": "session.update",
  "session": {
    "system_prompt": "<string>",
    "greeting":      "<string>",
    "input": {
      "format":       "audio/pcm | audio/pcmu | audio/pcma",
      "keyterms":     ["<string>"],
      "turn_detection": {
        "vad_threshold":   0.5,
        "min_silence_ms":  200,
        "max_silence_ms":  800,
        "interrupt_response": true
      }
    },
    "output": {
      "voice":  "<voice-name>",
      "format": "audio/pcm | audio/pcmu | audio/pcma"
    },
    "tools": [ <tool-schema-object>, ... ]
  }
}
```

### Field reference

| Field | Type | Default | Immutable | Description |
|-------|------|---------|-----------|-------------|
| `session.system_prompt` | string | — | Yes | System instructions for the agent. Sets personality, constraints, and behavior. Cannot be changed after `session.ready`. |
| `session.greeting` | string | — | Yes | The agent's first spoken utterance. Delivered immediately on `session.ready`. Cannot be changed after `session.ready`. |
| `session.input.format` | string | `audio/pcm` | Yes | Audio encoding of incoming audio. `audio/pcm` = signed 16-bit PCM at 24kHz. `audio/pcmu` = μ-law 8kHz (Twilio native). `audio/pcma` = A-law 8kHz. |
| `session.input.keyterms` | string[] | `[]` | No | Words/phrases to boost in transcription (names, product terms, etc.). |
| `session.input.turn_detection.vad_threshold` | float | `0.5` | No | Voice Activity Detection sensitivity. Range 0.0–1.0. Higher = less sensitive (less false positives). |
| `session.input.turn_detection.min_silence_ms` | integer | `200` | No | Minimum silence duration (ms) before a turn is considered ended. |
| `session.input.turn_detection.max_silence_ms` | integer | `800` | No | Maximum silence before the agent assumes the caller has stopped speaking. |
| `session.input.turn_detection.interrupt_response` | boolean | `true` | No | Whether the caller speaking mid-response interrupts the agent. Set `false` for IVR-style flows. |
| `session.output.voice` | string | `"Ava"` | No | TTS voice name. See voices list below. |
| `session.output.format` | string | `audio/pcm` | Yes | Audio encoding of outgoing `reply.audio` frames. Use `audio/pcmu` for Twilio to skip resampling. |
| `session.tools` | array | `[]` | No | Array of tool schema objects in JSON Schema format. |

### Tool schema object format

```json
{
  "name": "book_appointment",
  "description": "Book a nail appointment for the caller.",
  "parameters": {
    "type": "object",
    "properties": {
      "customer_name": { "type": "string",  "description": "Full name" },
      "service_id":    { "type": "integer", "description": "Service ID from list_services" },
      "datetime":      { "type": "string",  "description": "ISO 8601 appointment datetime" }
    },
    "required": ["customer_name", "service_id", "datetime"]
  }
}
```

---

## Server → Client Events

All events are JSON strings received on the WebSocket.

---

### `session.ready`

Emitted once the session is initialized and ready for audio. Save `session_id` immediately — it is needed for reconnects.

```json
{
  "type": "session.ready",
  "session_id": "sess_abc123xyz"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"session.ready"` |
| `session_id` | string | Unique session identifier. Store this for reconnect via `session.resume`. |

---

### `input.speech.started`

Emitted when the VAD detects the caller has started speaking.

```json
{
  "type": "input.speech.started"
}
```

---

### `input.speech.stopped`

Emitted when the VAD detects the caller has stopped speaking (end of turn).

```json
{
  "type": "input.speech.stopped"
}
```

---

### `transcript.user.delta`

Streaming partial transcription of the current caller utterance. Arrives in real time as the caller speaks. Use for UI display only — do not act on partial transcripts.

```json
{
  "type": "transcript.user.delta",
  "text": "I'd like to book a"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"transcript.user.delta"` |
| `text` | string | Partial transcript text so far in this turn. |

---

### `transcript.user`

Final, complete transcription of the caller's turn. Emitted after `input.speech.stopped`.

```json
{
  "type": "transcript.user",
  "text": "I'd like to book a gel manicure for Friday afternoon."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"transcript.user"` |
| `text` | string | Complete final transcript of the caller's turn. |

---

### `reply.started`

Emitted when the agent begins formulating a response (before any audio is delivered).

```json
{
  "type": "reply.started"
}
```

---

### `reply.audio`

One frame of agent TTS audio. Arrives in a stream of multiple events. The audio field is named **`data`** (not `audio`).

```json
{
  "type": "reply.audio",
  "data": "<base64-encoded-audio-bytes>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"reply.audio"` |
| `data` | string | Base64-encoded audio bytes in the format specified by `session.output.format`. **The field is `data`, not `audio`** — this is a common mistake. |

---

### `transcript.agent`

The text of what the agent said. Emitted after the agent's turn is complete.

```json
{
  "type": "transcript.agent",
  "text": "Sure! Let me check available Friday slots for a gel manicure."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"transcript.agent"` |
| `text` | string | Full text of the agent's spoken response. |

---

### `reply.done`

Signals the end of the agent's response turn.

```json
{
  "type": "reply.done",
  "status": "success"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"reply.done"` |
| `status` | string | `"success"` — turn completed normally. `"interrupted"` — caller spoke before the agent finished. |

On `"interrupted"`: flush the audio output buffer and discard any pending tool results from this turn.

---

### `tool.call`

The agent wants to invoke a tool. Dispatch to the tool-server and return `tool.result` **immediately**.

```json
{
  "type": "tool.call",
  "call_id": "call_7f3a2b",
  "name": "book_appointment",
  "arguments": {
    "customer_name": "Maria Garcia",
    "service_id": 2,
    "datetime": "2026-05-21T14:00:00"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"tool.call"` |
| `call_id` | string | Unique ID for this tool invocation. Must be echoed back in `tool.result`. |
| `name` | string | Tool name matching one of the names in `session.tools`. |
| `arguments` | object | Parsed JSON object of tool arguments. Ready to use — no need to `JSON.parse`. |

---

### `session.error`

A non-fatal error occurred within the session.

```json
{
  "type": "session.error",
  "message": "Tool result for call_id 'call_7f3a2b' timed out."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"session.error"` |
| `message` | string | Human-readable error description. |

---

## Client → Server Messages

All messages are JSON strings sent on the WebSocket.

---

### `session.update`

Configure or reconfigure the session. Send immediately on WebSocket open. Can be sent again mid-session to update non-immutable fields (tools, keyterms, VAD settings, voice).

```json
{
  "type": "session.update",
  "session": { ... }
}
```

See full schema in the [session.update section](#sessionupdate--full-schema) above.

---

### `input.audio`

Send caller audio to the agent. Call in a continuous loop as audio frames arrive from Twilio.

```json
{
  "type": "input.audio",
  "audio": "<base64-encoded-audio-bytes>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"input.audio"` |
| `audio` | string | Base64-encoded audio bytes in the format specified by `session.input.format`. |

---

### `tool.result`

Return the result of a tool call. **Send immediately after dispatching to the tool-server** — do not wait for `reply.done`.

```json
{
  "type": "tool.result",
  "call_id": "call_7f3a2b",
  "result": "{\"success\":true,\"appointment_id\":42,\"confirmation\":\"Booked!\"}"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"tool.result"` |
| `call_id` | string | Must match the `call_id` from the corresponding `tool.call` event. |
| `result` | string | **JSON-stringified** result object (i.e., `JSON.stringify(toolResponse)`). This is a string, not an object. |

---

### `session.resume`

Reconnect to an existing session after a network interruption. Must be sent within 30 seconds of disconnection.

```json
{
  "type": "session.resume",
  "session_id": "sess_abc123xyz"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"session.resume"` |
| `session_id` | string | The `session_id` saved from the original `session.ready` event. |

---

## Tool Call / Result Flow

```
AssemblyAI                        Bridge                       Tool-Server
    │                                │                               │
    │── tool.call ──────────────────►│                               │
    │   { call_id, name, arguments } │                               │
    │                                │── POST /tools/{name} ────────►│
    │                                │   (arguments as body)         │
    │                                │◄─ HTTP 200 { ... } ──────────│
    │◄─ tool.result ─────────────────│                               │
    │   { call_id,                   │  SEND IMMEDIATELY             │
    │     result: JSON.stringify(r) }│                               │
    │                                │                               │
    │── reply.audio (stream) ───────►│                               │
    │── reply.done ─────────────────►│                               │
```

**Critical timing rule:** Send `tool.result` as soon as you receive the HTTP response from the tool-server. Do not buffer, batch, or wait for any other event. AssemblyAI holds the agent's response pipeline open during tool execution — delays cause audible silence.

**Error handling:** If the tool-server returns 4xx or 5xx, still send a `tool.result` with a descriptive error string so the agent can respond gracefully:

```json
{
  "type": "tool.result",
  "call_id": "call_7f3a2b",
  "result": "{\"error\": \"Service temporarily unavailable. Please try again.\"}"
}
```

---

## Voices

### English (US)

| Name | Gender | Character |
|------|--------|-----------|
| `Ava` | Female | Warm, professional (default) |
| `Emma` | Female | Friendly, conversational |
| `Olivia` | Female | Clear, articulate |
| `Sophia` | Female | Energetic, upbeat |
| `Isabella` | Female | Calm, reassuring |
| `Liam` | Male | Confident, professional |
| `Noah` | Male | Friendly, approachable |
| `Ethan` | Male | Clear, neutral |

### English (UK)

| Name | Gender | Character |
|------|--------|-----------|
| `Amelia` | Female | Polished, formal |
| `Charlotte` | Female | Warm, natural |
| `George` | Male | Distinguished, clear |
| `Oliver` | Male | Conversational, friendly |

### Multilingual

| Name | Languages | Gender |
|------|-----------|--------|
| `Luna` | EN, ES, FR, DE, PT | Female |
| `Aria` | EN, ES, FR, IT, PT | Female |
| `Felix` | EN, ES, DE, FR | Male |
| `Zara` | EN, ES, FR, AR | Female |

---

## Turn Detection Tuning Guide

The `turn_detection` settings control how quickly the agent responds and how it handles overlapping speech.

| Setting | Lower value | Higher value | Recommended for phone |
|---------|-------------|--------------|----------------------|
| `vad_threshold` | More sensitive, picks up soft speech | Less sensitive, ignores background noise | `0.4`–`0.6` |
| `min_silence_ms` | Responds faster after pauses | Waits longer before ending turn | `150`–`300` ms |
| `max_silence_ms` | Cuts off callers who pause | More patient with slow speakers | `600`–`1000` ms |
| `interrupt_response` | `true`: caller can barge in | `false`: agent always finishes | `true` for natural conversation |

**Recommended Morty configuration:**

```json
"turn_detection": {
  "vad_threshold": 0.45,
  "min_silence_ms": 250,
  "max_silence_ms": 700,
  "interrupt_response": true
}
```

---

## Twilio Integration

### Skip resampling with `audio/pcmu`

Twilio delivers μ-law 8kHz audio. Rather than resampling to PCM16 24kHz for AssemblyAI and back, configure both input and output to use `audio/pcmu`:

```json
{
  "type": "session.update",
  "session": {
    "input":  { "format": "audio/pcmu" },
    "output": { "format": "audio/pcmu" }
  }
}
```

This eliminates the resampling layer in the bridge entirely:

- Twilio → base64 → `input.audio` (no decode needed)
- `reply.audio.data` → base64 → Twilio (no encode needed)

### Twilio media frame format

Twilio sends WebSocket messages like:

```json
{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "track": "inbound",
    "chunk": "1",
    "timestamp": "5",
    "payload": "<base64-encoded-mulaw>"
  }
}
```

Extract `media.payload` and send directly as `input.audio.audio` when using `audio/pcmu` input format.

---

## Reconnect Pattern

If the WebSocket disconnects unexpectedly:

1. Save `session_id` from `session.ready` at the start of every call.
2. On disconnect, immediately open a new WebSocket connection (with the same `Authorization` header or a fresh token).
3. On WebSocket open, send `session.resume` instead of `session.update`:

```json
{
  "type": "session.resume",
  "session_id": "sess_abc123xyz"
}
```

4. If `session.ready` is received again, the session resumed successfully. Continue streaming audio.
5. If `session.error` is received or the connection fails again, fall back to a new session via `session.update`.

**Time limit:** `session.resume` only works within **30 seconds** of the original disconnection. After 30 seconds, the session is discarded server-side and a new session must be created.

---

## Critical Gotchas

| # | Gotcha | Correct behavior |
|---|--------|-----------------|
| 1 | `reply.audio` field name | The audio payload is in the **`data`** field, not `audio`. Accessing `event.audio` returns `undefined`. |
| 2 | Bearer prefix required | Auth header must be `Authorization: Bearer <key>`. Using `Authorization: <key>` without `Bearer` causes auth failure. |
| 3 | Immutable fields | `system_prompt`, `greeting`, `input.format`, and `output.format` cannot be changed after `session.ready`. Set them correctly in the initial `session.update`. |
| 4 | `tool.result.result` is a string | The `result` field must be `JSON.stringify(obj)` — a string, not a nested object. |
| 5 | `tool.call.arguments` is already parsed | `arguments` is a JS object, not a JSON string. Do not `JSON.parse` it again. |
| 6 | Send `session.update` before `session.ready` | `session.update` must be sent on WebSocket `open` event, before `session.ready` arrives. |
| 7 | `tool.result` timing | Send immediately on HTTP response from tool-server. Never wait for `reply.done`. |
| 8 | Interrupted turn cleanup | On `reply.done` with `status: "interrupted"`, flush Twilio output buffer and discard any queued tool results from that turn. |
| 9 | Reconnect window | `session.resume` only works within 30 seconds of disconnect. After that, start fresh. |
| 10 | `input.audio` field name | When sending caller audio, the field is `audio` (not `data`). Opposite of `reply.audio`. |
