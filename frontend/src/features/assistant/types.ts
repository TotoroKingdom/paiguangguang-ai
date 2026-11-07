export type CapabilityKind = "tool" | "skill" | "mcp" | "agent";
export type CapabilityRef = { id: string; kind: CapabilityKind; name: string };
export type Capability = CapabilityRef & {
  description: string;
  category: string;
  icon: string;
  source: "system" | "personal";
  steps: string[];
  tools?: string[];
  content?: string;
};
export type ConnectorStatus =
  "connected" | "disconnected" | "unconfigured" | "connecting" | "error" | "unauthorized";
export type ConnectorConfig = {
  id: string;
  name: string;
  url: string;
  status: ConnectorStatus;
  lastError?: string;
};
export type DemoFile = { id: string; name: string; type: string; size: number; createdAt: string };
export type Draft = { text: string; capability: CapabilityRef | null; fileIds: string[] };
export type SendMessageInput = {
  conversationId?: string;
  text: string;
  capability?: CapabilityRef | null;
  fileIds: string[];
  simulateFailure?: boolean;
};
export type ExecutionStep = { title: string; detail: string };
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "generating" | "stopped" | "error";
  steps?: ExecutionStep[];
  capability?: CapabilityRef | null;
  attachments?: { id: string; name: string }[];
  request?: SendMessageInput;
};
export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
};
export type DemoState = {
  version: 1;
  conversations: Conversation[];
  favorites: string[];
  userSkills: Capability[];
  connectors: ConnectorConfig[];
  files: DemoFile[];
  draft: Draft;
  drafts?: Record<string, Draft>;
  activeDraftKey?: string;
};
export type DemoAction =
  | { type: "ACTIVATE_DRAFT"; key: string }
  | { type: "SET_DRAFT"; patch: Partial<Draft> }
  | { type: "TOGGLE_FAVORITE"; id: string }
  | { type: "IMPORT_SKILL"; skill: Capability }
  | { type: "DELETE_SKILL"; id: string }
  | { type: "UPSERT_CONNECTOR"; connector: ConnectorConfig }
  | { type: "ADD_FILES"; files: DemoFile[] }
  | { type: "DELETE_FILE"; id: string }
  | { type: "CREATE_CONVERSATION"; conversation: Conversation }
  | { type: "RENAME_CONVERSATION"; id: string; title: string }
  | { type: "DELETE_CONVERSATION"; id: string }
  | { type: "APPEND_MESSAGES"; conversationId: string; messages: ChatMessage[] }
  | {
      type: "UPDATE_MESSAGE";
      conversationId: string;
      messageId: string;
      patch: Partial<ChatMessage>;
    }
  | { type: "RESET"; state: DemoState };
