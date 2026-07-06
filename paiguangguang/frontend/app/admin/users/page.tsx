import { AuthGate } from "@/components/auth-gate";
import { UserManager } from "@/features/admin/admin-rbac-management";

export default function AdminUsersPage() {
  return (
    <AuthGate
      title="Admin Users"
      description="Manage user accounts, workspace membership, and role assignments."
    >
      <UserManager />
    </AuthGate>
  );
}
