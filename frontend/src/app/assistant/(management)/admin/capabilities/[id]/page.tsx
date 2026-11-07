import { AdminCapabilityDetail } from "@/features/admin/admin-capability-detail";

export default function Page({ params }: { params: { id: string } }) {
  return <AdminCapabilityDetail capabilityId={params.id} />;
}
