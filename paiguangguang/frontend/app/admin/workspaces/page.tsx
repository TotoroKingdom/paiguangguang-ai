import { AuthGate } from "@/components/auth-gate";
import { WorkspaceManager } from "@/features/admin/admin-rbac-management";

export default function AdminWorkspacesPage() {
  return (
    <AuthGate title="Admin Workspaces" description="Manage workspace records and the default workspace flag.">
      <WorkspaceManager />
    </AuthGate>
  );
}
