export type ConversationStatus = "active" | "archived";

export type ConversationTitleSource = "default" | "auto" | "manual";

export type ConversationActiveGeneration = {
  assistant_message_id: string;
  status: string;
  started_at: string | null;
};

export type ConversationData = {
  id: string;
  title: string;
  title_source: ConversationTitleSource;
  status: ConversationStatus;
  model: string;
  last_message_at: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ConversationDetailData = ConversationData & {
  active_generation: ConversationActiveGeneration | null;
};

export type ConversationPageData = {
  items: ConversationData[];
  next_cursor: string | null;
  has_more: boolean;
};

export type ConversationCreateRequest = {
  title?: string | null;
  model?: string | null;
};

export type ConversationUpdateRequest = {
  title?: string | null;
  model?: string | null;
};

export type DeleteResultData = {
  id: string;
  status: "deleted";
  cleanup_status: "pending" | "completed" | "retry";
};

