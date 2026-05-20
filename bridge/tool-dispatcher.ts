const TOOL_SERVER_URL =
  process.env.TOOL_SERVER_URL ?? "http://localhost:8000";

export interface ToolCallEvent {
  type: "tool.call";
  call_id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultEvent {
  type: "tool.result";
  call_id: string;
  result: string; // always JSON.stringify(value) — never a raw object
}

export function isToolCall(event: unknown): event is ToolCallEvent {
  return (
    typeof event === "object" &&
    event !== null &&
    (event as Record<string, unknown>)["type"] === "tool.call" &&
    typeof (event as Record<string, unknown>)["call_id"] === "string" &&
    typeof (event as Record<string, unknown>)["name"] === "string"
  );
}

export async function dispatchToolCall(
  event: ToolCallEvent
): Promise<ToolResultEvent> {
  const { call_id, name, arguments: args } = event;

  try {
    const response = await fetch(
      `${TOOL_SERVER_URL}/tools/${encodeURIComponent(name)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(args),
      }
    );

    const body: unknown = response.ok
      ? await response.json()
      : { error: `HTTP ${response.status}: ${await response.text().catch(() => response.statusText)}`, success: false };

    return { type: "tool.result", call_id, result: JSON.stringify(body) };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      type: "tool.result",
      call_id,
      result: JSON.stringify({ error: message, success: false }),
    };
  }
}
