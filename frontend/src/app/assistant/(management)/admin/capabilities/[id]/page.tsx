import { AdminCapabilityDetail } from "@/features/admin/admin-capability-detail";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AdminCapabilityDetail capabilityId={id} />;
}
