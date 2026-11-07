import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "智能助手 · 派广广",
  description: "工具、技能、MCP 与智能体的工作台与管理控制台",
};

export default function AssistantProductLayout({ children }: { children: ReactNode }) {
  return children;
}
