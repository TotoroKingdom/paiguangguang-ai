"use client";

import { AuthGate } from "@/components/auth-gate";
import { KnowledgeAgentWorkspace } from "@/features/knowledge-agent/knowledge-agent-workspace";

export function KnowledgeAgentShell() {
  return (
    <AuthGate
      title="Knowledge Agent"
      description="Upload or paste reference text, query the backend, and inspect sources only after signing in."
    >
      <KnowledgeAgentWorkspace />
    </AuthGate>
  );
}
