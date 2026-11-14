import { HomePageFrame } from "@/features/home/home-page-frame";

import { RagArchitecture } from "./rag-architecture";
import styles from "./rag-architecture.module.css";

export function RagPage() {
  return (
    <HomePageFrame
      activePage="rag"
      theme="spatial"
      footerLabel="TG / RAG"
      footerCopy="索引 · 检索 · 生成 · 反馈"
      mainClassName={styles.pageMain}
    >
      <RagArchitecture />
    </HomePageFrame>
  );
}
