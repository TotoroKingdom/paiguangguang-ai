export type MemoryListStatus = "candidate" | "active" | "superseded";

export type MemoryRecordStatus = MemoryListStatus | "deleted" | "failed";

export type MemoryStatus = MemoryListStatus;

export type MemoryType =
  | "preference"
  | "goal"
  | "project_context"
  | "explicit"
  | "fact"
  | "work_context";

export type MemoryData = {
  id: string;
  conversation_id: string | null;
  memory_type: MemoryType;
  content: string;
  importance: number;
  confidence: number;
  source_message_ids: string[];
  status: MemoryRecordStatus;
  last_accessed_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MemoryPageData = {
  items: MemoryData[];
  next_cursor: string | null;
  has_more: boolean;
};

export type MemoryUpdateRequest = {
  content?: string;
  status?: Extract<MemoryListStatus, "candidate" | "active">;
  expires_at?: string | null;
};
