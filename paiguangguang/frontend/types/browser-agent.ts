export type BrowserAgentRequest = {
  prompt: string;
  top_k: number;
};

export type BrowserSearchResultData = {
  title: string;
  url: string;
  snippet: string;
  score: number;
};

export type BrowserAgentStepKind = "plan" | "tool_call" | "observation" | "synthesis";

export type BrowserAgentStepData = {
  step_id: string;
  kind: BrowserAgentStepKind;
  title: string;
  detail: string;
  data: Record<string, unknown>;
};

export type BrowserAgentRunData = {
  prompt: string;
  search_query: string;
  steps: BrowserAgentStepData[];
  search_results: BrowserSearchResultData[];
  final_answer: string;
};
