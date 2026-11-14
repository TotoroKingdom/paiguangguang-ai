import { capabilityCatalog, createInitialState } from "./data";
import type { DemoAction, DemoState, Draft } from "./types";
export const STORAGE_KEY = "paiguangguang.assistant.v1";
export const LOCAL_STORAGE_KEY = "paiguangguang.assistant.local.v1";
export const MIGRATION_STORAGE_KEY = "paiguangguang.assistant.sqlite-migration.v1";
const obj = (x: unknown): x is Record<string, unknown> =>
  x !== null && typeof x === "object" && !Array.isArray(x);
const str = (x: unknown): x is string => typeof x === "string";
const strings = (x: unknown): x is string[] => Array.isArray(x) && x.every(str);
const kinds = ["tool", "skill", "mcp", "agent"];
const ref = (x: unknown) =>
  obj(x) && str(x.id) && str(x.name) && str(x.kind) && kinds.includes(x.kind);
const validDraft = (x: unknown) =>
  obj(x) && str(x.text) && (x.capability === null || ref(x.capability)) && strings(x.fileIds);
const emptyDraft = (): Draft => ({ text: "", capability: null, fileIds: [] });
const sortConversations = (conversations: DemoState["conversations"]) =>
  [...conversations].sort((a, b) => {
    const updated = b.updatedAt.localeCompare(a.updatedAt);
    return updated || b.id.localeCompare(a.id);
  });
const skill = (x: unknown) =>
  ref(x) &&
  obj(x) &&
  x.kind === "skill" &&
  x.source === "personal" &&
  str(x.description) &&
  str(x.category) &&
  str(x.icon) &&
  strings(x.steps) &&
  (x.tools === undefined || strings(x.tools)) &&
  (x.content === undefined || str(x.content));
const request = (x: unknown) =>
  obj(x) &&
  (x.conversationId === undefined || str(x.conversationId)) &&
  str(x.text) &&
  (x.capability == null || ref(x.capability)) &&
  strings(x.fileIds) &&
  (x.simulateFailure === undefined || typeof x.simulateFailure === "boolean");
const message = (x: unknown) =>
  obj(x) &&
  str(x.id) &&
  ["user", "assistant"].includes(String(x.role)) &&
  str(x.content) &&
  ["complete", "generating", "stopped", "error"].includes(String(x.status)) &&
  (x.steps === undefined ||
    (Array.isArray(x.steps) &&
      x.steps.every((s: unknown) => obj(s) && str(s.title) && str(s.detail)))) &&
  (x.capability == null || ref(x.capability)) &&
  (x.attachments === undefined ||
    (Array.isArray(x.attachments) &&
      x.attachments.every((a: unknown) => obj(a) && str(a.id) && str(a.name)))) &&
  (x.request === undefined || request(x.request));
const conversation = (x: unknown) =>
  obj(x) &&
  str(x.id) &&
  str(x.title) &&
  str(x.createdAt) &&
  str(x.updatedAt) &&
  Array.isArray(x.messages) &&
  x.messages.every(message);
const connector = (x: unknown) =>
  obj(x) &&
  str(x.id) &&
  str(x.name) &&
  str(x.url) &&
  ["connected", "disconnected", "unconfigured", "connecting", "error", "unauthorized"].includes(
    String(x.status),
  ) &&
  (x.lastError === undefined || str(x.lastError));
const file = (x: unknown) =>
  obj(x) &&
  str(x.id) &&
  str(x.name) &&
  str(x.type) &&
  typeof x.size === "number" &&
  Number.isFinite(x.size) &&
  x.size >= 0 &&
  str(x.createdAt);
export function restoreState(raw: string | null): DemoState {
  try {
    const x: unknown = JSON.parse(raw ?? "null");
    if (
      !obj(x) ||
      x.version !== 1 ||
      !Array.isArray(x.conversations) ||
      !x.conversations.every(conversation) ||
      !strings(x.favorites) ||
      !Array.isArray(x.userSkills) ||
      !x.userSkills.every(skill) ||
      !Array.isArray(x.connectors) ||
      !x.connectors.every(connector) ||
      !Array.isArray(x.files) ||
      !x.files.every(file) ||
      !validDraft(x.draft) ||
      (x.drafts !== undefined && (!obj(x.drafts) || !Object.values(x.drafts).every(validDraft))) ||
      (x.activeDraftKey !== undefined && !str(x.activeDraftKey))
    )
      return createInitialState();
    const state = x as unknown as DemoState;
    const capabilities = [...capabilityCatalog, ...state.userSkills];
    const cleanDraft = (draft: Draft): Draft => {
      const capability =
        draft.capability &&
        capabilities.find(
          (c) => c.id === draft.capability?.id && c.kind === draft.capability?.kind,
        );
      return {
        ...draft,
        capability: capability
          ? { id: capability.id, kind: capability.kind, name: capability.name }
          : null,
        fileIds: draft.fileIds.filter((id) => state.files.some((file) => file.id === id)),
      };
    };
    const drafts = Object.fromEntries(
      Object.entries(state.drafts ?? {}).map(([key, draft]) => [key, cleanDraft(draft)]),
    );
    return {
      ...state,
      activeDraftKey: state.activeDraftKey ?? "new",
      drafts,
      draft: cleanDraft(state.draft),
      conversations: state.conversations.map((c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.status === "generating" ? { ...m, status: "stopped" } : m,
        ),
      })),
      connectors: state.connectors.map((c) =>
        c.status === "connecting" ? { ...c, status: "disconnected" } : c,
      ),
    };
  } catch {
    return createInitialState();
  }
}
export function restoreLocalState(raw: string | null): DemoState {
  const restored = restoreState(raw);
  return { ...restored, conversations: [], catalog: createInitialState().catalog };
}
export function serializeLocalState(state: DemoState): string {
  return JSON.stringify({ ...state, conversations: [], catalog: [] });
}
export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case "ACTIVATE_DRAFT": {
      const oldKey = state.activeDraftKey ?? "new";
      if (oldKey === action.key) return state;
      const drafts = { ...state.drafts, [oldKey]: state.draft };
      return {
        ...state,
        drafts,
        activeDraftKey: action.key,
        draft: Object.prototype.hasOwnProperty.call(drafts, action.key)
          ? drafts[action.key]
          : emptyDraft(),
      };
    }
    case "SET_DRAFT":
      return { ...state, draft: { ...state.draft, ...action.patch } };
    case "TOGGLE_FAVORITE":
      return {
        ...state,
        favorites: state.favorites.includes(action.id)
          ? state.favorites.filter((id) => id !== action.id)
          : [...state.favorites, action.id],
      };
    case "IMPORT_SKILL":
      return { ...state, userSkills: [...state.userSkills, action.skill] };
    case "SET_SKILLS":
      return { ...state, userSkills: action.skills };
    case "DELETE_SKILL":
      return {
        ...state,
        drafts: Object.fromEntries(
          Object.entries(state.drafts ?? {}).map(([key, draft]) => [
            key,
            draft.capability?.id === action.id ? { ...draft, capability: null } : draft,
          ]),
        ),
        userSkills: state.userSkills.filter((s) => s.id !== action.id),
        favorites: state.favorites.filter((id) => id !== action.id),
        draft:
          state.draft.capability?.id === action.id
            ? { ...state.draft, capability: null }
            : state.draft,
      };
    case "UPSERT_CONNECTOR":
      return {
        ...state,
        connectors: state.connectors.some((c) => c.id === action.connector.id)
          ? state.connectors.map((c) => (c.id === action.connector.id ? action.connector : c))
          : [...state.connectors, action.connector],
      };
    case "ADD_FILES":
      return { ...state, files: [...state.files, ...action.files] };
    case "SET_FILES":
      return { ...state, files: action.files };
    case "DELETE_FILE":
      return {
        ...state,
        drafts: Object.fromEntries(
          Object.entries(state.drafts ?? {}).map(([key, draft]) => [
            key,
            { ...draft, fileIds: draft.fileIds.filter((id) => id !== action.id) },
          ]),
        ),
        files: state.files.filter((f) => f.id !== action.id),
        draft: { ...state.draft, fileIds: state.draft.fileIds.filter((id) => id !== action.id) },
      };
    case "CREATE_CONVERSATION":
      return {
        ...state,
        conversations: sortConversations([action.conversation, ...state.conversations]),
      };
    case "SET_CONVERSATIONS":
      return { ...state, conversations: sortConversations(action.conversations) };
    case "SET_CATALOG":
      return { ...state, catalog: action.catalog };
    case "UPSERT_CONVERSATION": {
      const found = state.conversations.some((c) => c.id === action.conversation.id);
      return {
        ...state,
        conversations: sortConversations(
          found
            ? state.conversations.map((c) =>
                c.id === action.conversation.id ? action.conversation : c,
              )
            : [action.conversation, ...state.conversations],
        ),
      };
    }
    case "RENAME_CONVERSATION":
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.id ? { ...c, title: action.title } : c,
        ),
      };
    case "DELETE_CONVERSATION": {
      const drafts = { ...state.drafts };
      delete drafts[action.id];
      const active = state.activeDraftKey === action.id;
      return {
        ...state,
        conversations: state.conversations.filter((c) => c.id !== action.id),
        drafts,
        ...(active ? { activeDraftKey: "new", draft: drafts.new ?? emptyDraft() } : {}),
      };
    }
    case "APPEND_MESSAGES":
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.conversationId
            ? {
                ...c,
                updatedAt: new Date().toISOString(),
                messages: [...c.messages, ...action.messages],
              }
            : c,
        ),
      };
    case "UPDATE_MESSAGE":
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.conversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === action.messageId ? { ...m, ...action.patch } : m,
                ),
              }
            : c,
        ),
      };
    case "RESET":
      return action.state;
  }
}
