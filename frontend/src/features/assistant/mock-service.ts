import { capabilityCatalog } from "./data";
import type {
  Capability,
  ConnectorConfig,
  DemoFile,
  ExecutionStep,
  SendMessageInput,
} from "./types";
export function createMockReply(
  input: SendMessageInput,
  files: DemoFile[],
  capabilities: Capability[] = capabilityCatalog,
): { reply: string; steps: ExecutionStep[] } {
  const text = input.text.toLowerCase();
  const name = input.capability?.name ?? "智能助手";
  const selected = files.filter((f) => input.fileIds.includes(f.id));
  let answer = "建议先明确目标和约束，再拆分任务、确定优先级并逐项验证结果。";
  if (/知识/.test(text + name) && /分析/.test(text + name))
    answer = "知识分析建议：围绕问题梳理主题、比较不同资料中的观点与证据，并标出冲突和待验证之处。";
  else if (/prd|需求/.test(text) || /需求|PRD/.test(name))
    answer =
      "需求概要：明确目标用户和核心问题；定义使用场景、功能范围与验收标准；补充风险和待确认事项。";
  else if (/搜索|查找|search/.test(text) || /搜索/.test(name))
    answer =
      "搜索方案：提炼关键词，比较多个来源，并记录出处与更新时间。当前为模拟结果，请在实际使用时核验来源。";
  else if (/知识|查询/.test(text) || /知识/.test(name))
    answer = "知识查询建议：先限定主题和范围，再检索相关资料，按相关性整理结论与引用。";
  else if (/分析|数据/.test(text) || /分析|数据/.test(name))
    answer = "分析建议：明确指标与口径，检查数据质量，比较趋势与异常，再验证可能的原因。";
  if (selected.length)
    answer += `\n\n已选择附件：${selected.map((f) => f.name).join("、")}。演示仅使用文件元信息，不读取文件内容；可结合实际文件补充上下文后进一步分析。`;
  const capability = capabilities.find((item) => item.id === input.capability?.id);
  let steps: ExecutionStep[];
  switch (input.capability?.kind) {
    case "tool":
      steps = [
        { title: "调用参数", detail: `工具：${name}；任务：${input.text.slice(0, 80)}` },
        { title: "工具结果", detail: "模拟工具返回示例结果，未执行实际调用。" },
      ];
      break;
    case "skill":
      steps = (capability?.steps ?? ["理解目标", "整理内容", "生成结果"]).map((title) => ({
        title,
        detail: `按「${name}」的步骤处理当前任务。`,
      }));
      break;
    case "mcp":
      steps = [
        { title: "模拟连接", detail: `模拟连接${name}。` },
        { title: "模拟查询", detail: `按任务“${input.text.slice(0, 80)}”查询示例数据。` },
        { title: "来源摘要", detail: "结果为模拟资料，未访问外部服务。" },
      ];
      break;
    case "agent":
      steps = [
        { title: "制定计划", detail: capability?.steps.join(" → ") ?? "拆解目标并制定计划。" },
        { title: "选择工具", detail: `模拟使用：${capability?.tools?.join("、") ?? "相关工具"}。` },
        { title: "形成结论", detail: "综合模拟结果并整理建议。" },
      ];
      break;
    default:
      steps = [
        { title: "理解任务", detail: "识别问题和目标。" },
        { title: "整理建议", detail: "组织模拟回复。" },
      ];
  }
  return { reply: `针对“${input.text.slice(0, 80)}”，${answer}`, steps };
}
export async function testConnection(
  config: ConnectorConfig,
  simulateFailure = false,
): Promise<ConnectorConfig> {
  await new Promise((resolve) => setTimeout(resolve, 300));
  let valid = false;
  try {
    const url = new URL(config.url);
    valid = ["http:", "https:"].includes(url.protocol) && !!url.hostname;
  } catch {
    /* Invalid URL. */
  }
  if (!valid || simulateFailure)
    return {
      ...config,
      status: "error",
      lastError: valid ? "模拟连接失败，请重试。" : "请输入有效的 HTTP 或 HTTPS 地址。",
    };
  const { lastError: _lastError, ...rest } = config;
  return { ...rest, status: "connected" };
}
