import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AssistantProvider } from "@/features/assistant/provider";
import { AssistantWorkspace } from "@/features/assistant/assistant-workspace";
import "./assistant.css";

export const metadata: Metadata = {
  title: "智能助手 · 派广广",
  description: "工具、技能、MCP 与智能体的前端交互原型",
};
export default function AssistantLayout({ children }: { children: ReactNode }) {
  return (
    <AssistantProvider>
      <AssistantWorkspace>{children}</AssistantWorkspace>
    </AssistantProvider>
  );
}
