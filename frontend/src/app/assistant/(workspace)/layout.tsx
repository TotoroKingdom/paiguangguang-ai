import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AssistantProvider } from "@/features/assistant/provider";
import { AssistantWorkspace } from "@/features/assistant/assistant-workspace";
import "../assistant.css";

export const metadata: Metadata = {
  title: "智能助手工作台 · 派广广",
  description: "聊天、工具、技能、MCP 与智能体工作台",
};
export default function AssistantLayout({ children }: { children: ReactNode }) {
  return (
    <AssistantProvider>
      <AssistantWorkspace>{children}</AssistantWorkspace>
    </AssistantProvider>
  );
}
