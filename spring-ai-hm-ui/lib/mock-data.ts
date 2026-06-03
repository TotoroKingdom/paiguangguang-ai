import type { Conversation, Message } from "@/types/chat";

export const mockConversations: Conversation[] = [
  {
    id: "conv-product-roadmap",
    messages: [],
    title: "Product roadmap draft",
    updatedAt: "Today",
    preview: "Turn the launch notes into an executive summary.",
  },
  {
    id: "conv-next-layout",
    messages: [],
    title: "Next.js layout help",
    updatedAt: "Yesterday",
    preview: "Explain route groups and shared layouts.",
  },
  {
    id: "conv-data-ideas",
    messages: [],
    title: "Dashboard data ideas",
    updatedAt: "Mon",
    preview: "Create compact widgets for operational metrics.",
  },
  {
    id: "conv-email",
    messages: [],
    title: "Customer email polish",
    updatedAt: "May 28",
    preview: "Make the message warmer and more concise.",
  },
  {
    id: "conv-research",
    messages: [],
    title: "Research synthesis",
    updatedAt: "May 24",
    preview: "Cluster interview findings into themes.",
  },
];

export const mockMessages: Message[] = [
  {
    id: "msg-1",
    role: "assistant",
    content:
      "Good evening. I have the workspace ready. What would you like to shape first?",
    createdAt: "8:18 PM",
    status: "complete",
  },
  {
    id: "msg-2",
    role: "user",
    content:
      "Help me turn our release notes into a short product update for leadership.",
    createdAt: "8:19 PM",
    status: "complete",
  },
  {
    id: "msg-3",
    role: "assistant",
    content:
      "Absolutely. Here is a tighter version with the signal pulled forward:\n\nThis release improves setup speed, adds clearer account-level controls, and reduces manual follow-up for support teams. The most visible customer impact is a smoother onboarding path, while the biggest operational win is better auditability across workspace changes.",
    createdAt: "8:20 PM",
    prompt:
      "Help me turn our release notes into a short product update for leadership.",
    status: "complete",
  },
  {
    id: "msg-4",
    role: "user",
    content:
      "Nice. Can you make it sound a little more confident without making it too salesy?",
    createdAt: "8:22 PM",
    status: "complete",
  },
  {
    id: "msg-5",
    role: "assistant",
    content:
      "This release makes the product easier to adopt and easier to govern. Teams can get started faster, admins have clearer controls, and support has better visibility into workspace activity. Together, these changes reduce friction in the first week of use and give larger customers more confidence as they scale.",
    createdAt: "8:23 PM",
    prompt:
      "Nice. Can you make it sound a little more confident without making it too salesy?",
    status: "complete",
  },
];

mockConversations[0].messages = mockMessages;
