import { generateText, tool } from "ai";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic();

// surfacelock: prompt id=agent.ts.system
export const SYSTEM_PROMPT = `You are a meticulous code reviewer for a TypeScript
codebase. Prefer explicit types, flag any use of "any", and always suggest a
test that would have caught the bug you are describing.`;

const MODEL = "claude-3-5-sonnet-latest";

export const weatherTool = tool({
  name: "get_weather",
  description: "Get the current weather for a city",
  parameters: {
    type: "object",
    properties: {
      city: { type: "string" },
      units: { type: "string" },
    },
  },
});

export async function review(code: string) {
  return generateText({
    model: MODEL,
    system: SYSTEM_PROMPT,
    prompt: code,
    tools: { weatherTool },
  });
}
