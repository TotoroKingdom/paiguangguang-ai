import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Suspense } from "react";
import { AuthProvider } from "@/components/auth-provider";
import { RouteGuard } from "@/components/route-guard";
import { SiteNav } from "@/components/site-nav";
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
              <SiteNav />
              <main className="w-full px-4 py-6 sm:px-6 md:py-8 lg:px-8">{children}</main>
            </RouteGuard>
          </Suspense>
        </AuthProvider>
      </body>
    </html>
  );
}
