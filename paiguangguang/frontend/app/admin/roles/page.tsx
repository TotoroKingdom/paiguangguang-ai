import { AuthGate } from "@/components/auth-gate";
import { RoleManager } from "@/features/admin/admin-rbac-management";

export default function AdminRolesPage() {
  return (
    <AuthGate title="Admin Roles" description="Manage role definitions and their assigned permissions.">
      <RoleManager />
    </AuthGate>
  );
}
