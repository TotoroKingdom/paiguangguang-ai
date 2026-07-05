import { AdminDocumentManagement } from "@/features/admin/admin-document-management";
import { AdminRbacManagement } from "@/features/admin/admin-rbac-management";

export function AdminShell() {
  return (
    <div className="space-y-8">
      <AdminDocumentManagement />
      <AdminRbacManagement />
    </div>
  );
}
