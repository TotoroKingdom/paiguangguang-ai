import { postJson } from "@/lib/api";
import type { OfficeAgentRequest, OfficeAgentRunData } from "@/types/office-agent";

export function runOfficeAgent(request: OfficeAgentRequest) {
  return postJson<OfficeAgentRunData, OfficeAgentRequest>("/api/v1/agents/office/run", request);
}
