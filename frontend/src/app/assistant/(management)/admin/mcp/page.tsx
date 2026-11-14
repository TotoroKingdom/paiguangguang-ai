import { AdminCapabilityList } from "@/features/admin/admin-capability-list";
import { AdminMcpServers } from "@/features/auth/admin-mcp";

export default function Page() {
  return (
    <div>
      <AdminMcpServers />
      <AdminCapabilityList kind="mcp" />
    </div>
  );
}
