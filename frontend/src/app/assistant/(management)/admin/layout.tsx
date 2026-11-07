import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AdminProvider } from "@/features/admin/admin-provider";
import { AdminFrame } from "@/features/admin/admin-shell";
import "./admin.css";

export const metadata: Metadata = {
  title: "管理控制台 · 派广广",
  description: "智能助手能力注册、版本发布与运行治理",
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminProvider>
      <AdminFrame>{children}</AdminFrame>
    </AdminProvider>
  );
}
