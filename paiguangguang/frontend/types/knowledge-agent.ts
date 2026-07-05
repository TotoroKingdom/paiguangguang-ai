export type KnowledgeDocumentCreateRequest = {
  title?: string | null;
  text: string;
};

export type KnowledgeDocumentData = {
  doc_id: string;
  title: string | null;
  text_length: number;
  content_hash: string;
  owner_user_id: string | null;
  workspace_id: string | null;
  permission_scope: string | null;
  status: string;
  parse_status: string;
  chunk_status: string;
  embedding_status: string;
  index_status: string;
  is_deleted: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeIngestRequest = {
  doc_id?: string | null;
  title?: string | null;
  text?: string | null;
  chunk_size?: number;
  chunk_overlap?: number;
  reindex?: boolean;
};

export type KnowledgeChunkData = {
  chunk_id: string;
  index: number;
  start_char: number;
  end_char: number;
  text: string;
};

export type KnowledgeIngestData = {
  doc_id: string;
  title: string | null;
  chunk_size: number;
  chunk_overlap: number;
  text_length: number;
  chunk_count: number;
  chunks: KnowledgeChunkData[];
  document: KnowledgeDocumentData;
  job: KnowledgeIngestionJobData;
};

export type KnowledgeQueryRequest = {
  question: string;
  collection: string;
  top_k: number;
  include_debug?: boolean;
};

export type KnowledgeSourceData = {
  doc_id: string;
  chunk_id: string;
  title: string | null;
  page_number: number | null;
  chunk_index: number;
  text: string;
  score: number;
  rerank_score: number | null;
  route_scores: Record<string, number>;
  metadata: Record<string, unknown>;
};

export type KnowledgeQueryRewriteMetadata = {
  enabled: boolean;
  model: string | null;
  status: string;
  fallback_reason: string | null;
  rewritten_query_count: number;
};

export type KnowledgeQueryRewriteData = {
  original_question: string;
  rewritten_queries: string[];
  metadata: KnowledgeQueryRewriteMetadata;
};

export type KnowledgeQueryData = {
  answer: string;
  sources: KnowledgeSourceData[];
  rewrite?: KnowledgeQueryRewriteData | null;
  debug?: KnowledgeQueryDebugData | null;
};

export type KnowledgeQueryDebugData = {
  rewrites: KnowledgeQueryRewriteData | null;
  vector_hits: KnowledgeSourceData[];
  keyword_hits: KnowledgeSourceData[];
  fusion: KnowledgeSourceData[];
  rerank: KnowledgeSourceData[];
  selected_context: KnowledgeSourceData[];
  citations: KnowledgeSourceData[];
  latency_ms: number;
  model_usage: Record<string, unknown>;
};

export type KnowledgeIngestResult = {
  document: KnowledgeDocumentData;
  ingestion: KnowledgeIngestData;
};

export type KnowledgeIngestionJobData = {
  job_id: string;
  document_id: string;
  status: string;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  is_reindex: boolean;
  chunk_size: number | null;
  chunk_overlap: number | null;
  created_at: string;
  updated_at: string;
};
