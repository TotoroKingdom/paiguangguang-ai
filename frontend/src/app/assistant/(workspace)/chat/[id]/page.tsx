import { AssistantChat } from "@/features/assistant/assistant-chat";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssistantChat conversationId={id} />;
}
