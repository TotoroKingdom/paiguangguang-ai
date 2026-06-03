export type MessageRole = "assistant" | "user";

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  prompt?: string;
  status?: "complete" | "error" | "stopped" | "streaming";
};

export type Conversation = {
  id: string;
  messages: Message[];
  title: string;
  preview: string;
  updatedAt: string;
};
