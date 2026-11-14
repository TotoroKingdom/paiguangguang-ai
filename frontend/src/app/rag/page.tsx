import { RagPage as RagPageView } from "@/features/rag/rag-page";

export const metadata = {
  title: "RAG 知识检索系统 · TotoroKingdom",
  description: "RAG 的离线索引、在线混合检索、重排与引用生成，以及数据更新和质量反馈两条回环。"
};

export default function RagRoutePage() {
  return <RagPageView />;
}
