import { AuthGate } from "@/components/auth-gate";
import { PermissionManager } from "@/features/admin/admin-rbac-management";

export default function AdminPermissionsPage() {
  return (
    <AuthGate title="Admin Permissions" description="Manage the permission catalog that powers role access.">
      <PermissionManager />
    </AuthGate>
  );
}
