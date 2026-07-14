import { ChatbotShell } from "@/features/chatbot/components/chatbot-shell";
import { notFound } from "next/navigation";
import { isChatbotEnabled } from "@/lib/features";

export default function ChatBotPage() {
  if (!isChatbotEnabled()) {
    notFound();
  }
  return <ChatbotShell />;
}
