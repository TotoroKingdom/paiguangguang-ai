export type OfficeWorkflow = "generate_report" | "summarize_data" | "write_email";

export type OfficeAgentRequest = {
  workflow: OfficeWorkflow;
  prompt: string;
};

export type OfficeAgentStepKind = "plan" | "tool_call" | "observation" | "synthesis";

export type OfficeAgentStepData = {
  step_id: string;
  kind: OfficeAgentStepKind;
  title: string;
  detail: string;
  data: Record<string, unknown>;
};

export type OfficeAgentFinalOutputData = {
  artifact_type: "summary" | "report" | "email";
  title: string;
  summary: string;
  content: string;
  metadata: Record<string, unknown>;
};

export type OfficeAgentRunData = {
  workflow: string;
  prompt: string;
  steps: OfficeAgentStepData[];
  final_output: OfficeAgentFinalOutputData;
};
