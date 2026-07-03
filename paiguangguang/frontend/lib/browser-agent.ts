import { postJson } from "@/lib/api";
import type { BrowserAgentRequest, BrowserAgentRunData } from "@/types/browser-agent";

export function runBrowserAgent(request: BrowserAgentRequest) {
  return postJson<BrowserAgentRunData, BrowserAgentRequest>("/api/v1/agents/browser/run", request);
}
