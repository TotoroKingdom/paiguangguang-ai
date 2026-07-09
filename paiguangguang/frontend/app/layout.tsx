import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Suspense } from "react";
import { AuthProvider } from "@/components/auth-provider";
import { AppShell } from "@/components/app-shell";
import { RouteGuard } from "@/components/route-guard";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pai Guangguang AI Portfolio",
  description: "Interactive AI engineering portfolio system"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Suspense fallback={null}>
            <RouteGuard>
              <AppShell>{children}</AppShell>
            </RouteGuard>
          </Suspense>
        </AuthProvider>
      </body>
    </html>
  );
}
