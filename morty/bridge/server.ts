import { config as dotenvConfig } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
dotenvConfig({ path: resolve(dirname(fileURLToPath(import.meta.url)), ".env") });

import express from "express";
import { createServer } from "http";
import { WebSocket, WebSocketServer } from "ws";
import { IncomingMessage } from "http";

const TOOL_SERVER_URL = process.env.TOOL_SERVER_URL ?? "http://localhost:8000";
const ASSEMBLYAI_API_KEY =
  process.env.ASSEMBLYAI_API_KEY ?? "c65d449af3f24b93b92b6a4b31e65a31";
const WEBHOOK_BASE = process.env.WEBHOOK_BASE ?? "";
const PORT = parseInt(process.env.PORT ?? "3001", 10);

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

// ── TwiML webhook ─────────────────────────────────────────────────────────────
app.post("/voice", (req, res) => {
  const host = WEBHOOK_BASE.replace(/^https?:\/\//, "") || req.headers.host;
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://${host}/media-stream"/>
  </Connect>
</Response>`;
  res.type("text/xml").send(twiml);
});

app.get("/health", (_req, res) => res.json({ status: "ok" }));

// ── HTTP + WS server ──────────────────────────────────────────────────────────
const server = createServer(app);
const wss = new WebSocketServer({ server, path: "/media-stream" });

wss.on("connection", (twilioWs: WebSocket, _req: IncomingMessage) => {
  console.log("[bridge] Twilio connected");

  let streamSid: string | null = null;
  let aaiWs: WebSocket | null = null;
  let callActive = true;
  let hangUpPending = false;

  async function openAssemblyAI() {
    // Fetch schemas + prompts in parallel
    const [schemasRes, promptsRes] = await Promise.all([
      fetch(`${TOOL_SERVER_URL}/tools/schemas`),
      fetch(`${TOOL_SERVER_URL}/tools/prompts`),
    ]);

    if (!schemasRes.ok || !promptsRes.ok) {
      console.error("[bridge] Failed to fetch schemas or prompts from tool-server");
      twilioWs.close();
      return;
    }

    const schemas = (await schemasRes.json()) as { tools: object[] };
    const prompts = (await promptsRes.json()) as {
      system_prompt: string;
      greeting: string;
    };

    console.log(`[bridge] Loaded ${schemas.tools.length} tools from tool-server`);

    const ws = new WebSocket("wss://agents.assemblyai.com/v1/realtime", {
      headers: { Authorization: `Bearer ${ASSEMBLYAI_API_KEY}` },
    });

    aaiWs = ws;

    ws.on("open", () => {
      console.log("[bridge] AssemblyAI connected — sending session.update");
      ws.send(
        JSON.stringify({
          type: "session.update",
          session: {
            system_prompt: prompts.system_prompt,
            greeting: prompts.greeting,
            input: {
              type: "audio",
              format: { encoding: "audio/pcmu" },
              keyterms: [
                "Morty",
                "manicure",
                "pedicure",
                "OPI",
                "gel",
                "acrylic",
              ],
              turn_detection: {
                vad_threshold: 0.45,
                min_silence: 250,
                max_silence: 700,
                interrupt_response: true,
              },
            },
            output: {
              type: "audio",
              voice: "emma",
              format: { encoding: "audio/pcmu" },
            },
            tools: schemas.tools,
          },
        })
      );
    });

    ws.on("message", async (raw: Buffer | string) => {
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw.toString());
      } catch {
        return;
      }

      const type = event.type as string;

      if (type === "session.ready") {
        console.log("[bridge] session.ready — session_id:", event.session_id);
      }

      // ── Audio from AAI → Twilio ────────────────────────────────────────────
      if (type === "reply.audio" && streamSid) {
        twilioWs.send(
          JSON.stringify({
            event: "media",
            streamSid,
            media: { payload: event.data },
          })
        );
      }

      // ── Barge-in: caller started speaking ─────────────────────────────────
      if (type === "input.speech.started" && streamSid) {
        twilioWs.send(JSON.stringify({ event: "clear", streamSid }));
      }

      // ── Tool dispatch ──────────────────────────────────────────────────────
      if (type === "tool.call") {
        const callId = event.call_id as string;
        const toolName = event.name as string;
        const toolArgs = event.arguments as Record<string, unknown>;

        console.log(`[bridge] tool.call: ${toolName}`, toolArgs);

        // hang_up is special — close call after a short delay
        if (toolName === "hang_up") {
          ws.send(
            JSON.stringify({
              type: "tool.result",
              call_id: callId,
              result: JSON.stringify({ success: true }),
            })
          );
          if (!hangUpPending) {
            hangUpPending = true;
            setTimeout(() => closeCall(), 1500);
          }
          return;
        }

        let result: object;
        try {
          const res = await fetch(`${TOOL_SERVER_URL}/tools/${toolName}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(toolArgs ?? {}),
          });
          result = await res.json();
          if (!res.ok) {
            result = {
              error:
                (result as Record<string, unknown>).error ??
                `Tool server error: ${res.status}`,
            };
          }
        } catch (err) {
          result = { error: "Could not reach tool server. Please try again." };
        }

        console.log(`[bridge] tool.result: ${toolName}`, result);

        if (ws.readyState === WebSocket.OPEN) {
          ws.send(
            JSON.stringify({
              type: "tool.result",
              call_id: callId,
              result: JSON.stringify(result),
            })
          );
        }
      }

      if (type === "session.error") {
        console.error("[bridge] session.error:", event);
      }
    });

    ws.on("close", (code, reason) => {
      console.log(`[bridge] AssemblyAI closed: ${code} ${reason}`);
      if (callActive) closeCall();
    });

    ws.on("error", (err) => {
      console.error("[bridge] AssemblyAI WS error:", err.message);
    });
  }

  function closeCall() {
    if (!callActive) return;
    callActive = false;
    console.log("[bridge] closing call");
    try {
      aaiWs?.close();
    } catch {}
    try {
      twilioWs.close();
    } catch {}
  }

  // ── Twilio → bridge ────────────────────────────────────────────────────────
  twilioWs.on("message", (raw: Buffer | string) => {
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }

    const event = msg.event as string;

    if (event === "connected") {
      console.log("[bridge] Twilio stream connected — opening AssemblyAI");
      openAssemblyAI().catch((err) => {
        console.error("[bridge] Failed to open AssemblyAI:", err);
        twilioWs.close();
      });
      return;
    }

    if (event === "start") {
      const startData = msg.start as Record<string, unknown>;
      streamSid = startData?.streamSid as string;
      console.log("[bridge] streamSid:", streamSid);
      return;
    }

    if (event === "media") {
      const media = msg.media as Record<string, unknown>;
      if (media?.track === "inbound" && aaiWs?.readyState === WebSocket.OPEN) {
        aaiWs.send(
          JSON.stringify({ type: "input.audio", audio: media.payload })
        );
      }
      return;
    }

    if (event === "stop") {
      console.log("[bridge] Twilio stop — hanging up");
      closeCall();
    }
  });

  twilioWs.on("close", () => {
    console.log("[bridge] Twilio WS closed");
    closeCall();
  });

  twilioWs.on("error", (err) => {
    console.error("[bridge] Twilio WS error:", err.message);
  });
});

server.listen(PORT, () => {
  console.log(`[bridge] Listening on port ${PORT}`);
  console.log(`[bridge] POST /voice  →  TwiML webhook`);
  console.log(`[bridge] WS   /media-stream  →  Twilio stream`);
});
