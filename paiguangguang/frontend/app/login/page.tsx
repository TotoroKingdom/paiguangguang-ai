import { Suspense } from "react";

import { LoginPanel } from "@/features/auth/login-panel";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="text-sm text-ink/60">Loading login form...</div>}>
      <LoginPanel />
    </Suspense>
  );
}
