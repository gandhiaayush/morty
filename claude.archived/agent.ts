import Anthropic from "@anthropic-ai/sdk";
import { config } from "../../config";
import { Message } from "../supabase/sessions";
import { WORKER_TOOLS } from "./tools";
import { callWorkerTool } from "../notion/worker";

const anthropic = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });

const TODAY = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
});

const SYSTEM_PROMPT = `You are a voice assistant for a dry cleaning business.
You handle inbound customer calls about their orders.
Today's date is ${TODAY}.

CALL FLOW:
1. At the start of every call, immediately call getOrderByPhone with the caller's phone number.
2. If no order found, try searchOrdersByName as fallback (ask for their name first).
3. If multiple orders found, ask which one they're calling about (reference garmentType or expectedDate).
4. Always confirm the customer's identity before making any changes.

VERIFICATION CYCLE — run this after every tool call that returns order data:
- Check the _verify field in the tool response. If it is non-null, follow its instruction exactly before proceeding.
- If multiple orders returned: ask "Are you calling about your [garmentType] or your [other garmentType]?" Do NOT read any order details until the customer confirms which one.
- If getOrderById was used (no phone check): confirm "Just to verify — am I speaking with [customerName]?" before any write operation.
- If the returned garmentType, expectedDate, or price seems inconsistent with what the customer just said, re-query with getOrderById using the order ID the customer mentioned, then compare. Trust the re-queried result.

PRICING RULES:
- For expedited orders: quote the price, then say "Expedited slots can fill up — would you like someone to call you back to confirm capacity before we commit?"
- If lookupPrice returns a notes field (e.g. "Call for quote on heavily beaded"), read it to the customer and offer a callback via requestCallback.
- After any setOrderType or updateGarmentType call, always chain: lookupPrice → updateOrderPrice.

RESPONSE RULES:
- Max 3 sentences per response (this is read aloud over the phone).
- Never read out pageId or internal IDs to the customer.
- Always end with a question or confirmation to keep the conversation moving.`;

export async function agentTurn(
  messages: Message[],
  _callerRole: "owner" | "consumer",
  _callSid: string,
  _callerPhone: string
): Promise<{ responseText: string; actionsTaken: string[] }> {
  const actionsTaken: string[] = [];

  const claudeMessages: Anthropic.MessageParam[] = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  let response = await anthropic.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 512,
    system: SYSTEM_PROMPT,
    tools: WORKER_TOOLS,
    messages: claudeMessages,
  });

  while (response.stop_reason === "tool_use") {
    const toolUseBlocks = response.content.filter(
      (b): b is Anthropic.ToolUseBlock => b.type === "tool_use"
    );

    const toolResults = await Promise.all(
      toolUseBlocks.map(async (toolUse: Anthropic.ToolUseBlock) => {
        const result = await callWorkerTool(
          toolUse.name,
          toolUse.input as Record<string, unknown>
        );
        actionsTaken.push(toolUse.name);
        return {
          type: "tool_result" as const,
          tool_use_id: toolUse.id,
          content: JSON.stringify(result),
        };
      })
    );

    claudeMessages.push({ role: "assistant", content: response.content });
    claudeMessages.push({ role: "user", content: toolResults });

    response = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 512,
      system: SYSTEM_PROMPT,
      tools: WORKER_TOOLS,
      messages: claudeMessages,
    });
  }

  const textBlock = response.content.find(
    (b: Anthropic.ContentBlock): b is Anthropic.TextBlock => b.type === "text"
  );
  const responseText =
    textBlock?.text ??
    "I'm having trouble right now. Could you try again or call back in a moment?";

  return { responseText, actionsTaken };
}
// archived: superseded by morty/ AssemblyAI stack
