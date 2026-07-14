export function isChatbotEnabled(value = process.env.NEXT_PUBLIC_CHATBOT_ENABLED) {
  return value?.trim().toLowerCase() !== "false";
}
