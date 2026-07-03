export type KnowledgeDocumentCreateRequest = {
  title?: string | null;
  text: string;
};

export type KnowledgeDocumentData = {
  doc_id: string;
  title: string | null;
  text_length: number;
  content_hash: string;
};

export type KnowledgeIngestRequest = {
  doc_id?: string | null;
  title?: string | null;
  text?: string | null;
  chunk_size?: number;
  chunk_overlap?: number;
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
};

export type KnowledgeQueryRequest = {
  question: string;
  collection: string;
  top_k: number;
};

export type KnowledgeSourceData = {
  doc_id: string;
  chunk_id: string;
  text: string;
  score: number;
};

export type KnowledgeQueryData = {
  answer: string;
  sources: KnowledgeSourceData[];
};

export type KnowledgeIngestResult = {
  document: KnowledgeDocumentData;
  ingestion: KnowledgeIngestData;
};
