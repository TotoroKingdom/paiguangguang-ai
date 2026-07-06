import { getJson, postJson } from "@/lib/api";
import { getStoredAuthToken } from "@/lib/auth";
import type {
  KnowledgeCollectionsData,
  KnowledgeDocumentCreateRequest,
  KnowledgeDocumentData,
  KnowledgeIngestData,
  KnowledgeIngestRequest,
  KnowledgeIngestResult,
  KnowledgeQueryData,
  KnowledgeQueryRequest,
} from "@/types/knowledge-agent";

const DEFAULT_KNOWLEDGE_COLLECTION = "portfolio_knowledge";

export function getDefaultKnowledgeCollection() {
  return DEFAULT_KNOWLEDGE_COLLECTION;
}

export function registerKnowledgeDocument(request: KnowledgeDocumentCreateRequest) {
  return postJson<KnowledgeDocumentData, KnowledgeDocumentCreateRequest>("/api/v1/rag/documents", request, {
    token: getStoredAuthToken(),
  });
}

export function ingestKnowledgeDocument(request: KnowledgeIngestRequest) {
  return postJson<KnowledgeIngestData, KnowledgeIngestRequest>("/api/v1/rag/ingest", request, {
    token: getStoredAuthToken(),
  });
}

export function listKnowledgeCollections() {
  return getJson<KnowledgeCollectionsData>("/api/v1/rag/collections", {
    token: getStoredAuthToken(),
  });
}

export async function ingestKnowledgeText(
  request: KnowledgeDocumentCreateRequest & KnowledgeIngestRequest
): Promise<KnowledgeIngestResult> {
  const document = await registerKnowledgeDocument({
    title: request.title ?? undefined,
    text: request.text ?? "",
  });

  const ingestion = await ingestKnowledgeDocument({
    doc_id: document.doc_id,
    chunk_size: request.chunk_size,
    chunk_overlap: request.chunk_overlap,
  });

  return { document, ingestion };
}

export function queryKnowledgeAgent(request: KnowledgeQueryRequest) {
  return postJson<KnowledgeQueryData, KnowledgeQueryRequest>("/api/v1/rag/query", request, {
    token: getStoredAuthToken(),
  });
}
