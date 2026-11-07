import { AssistantChat } from "@/features/assistant/assistant-chat";
export default function Page({ params }: { params: { id: string } }) {
  return <AssistantChat conversationId={params.id} />;
}
