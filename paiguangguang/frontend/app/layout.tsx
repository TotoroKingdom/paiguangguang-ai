import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/auth-provider";
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
          <SiteNav />
          <main className="mx-auto max-w-6xl px-5 py-10 md:py-14">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
