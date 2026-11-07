import type { Capability, CapabilityKind, DemoState } from "./types";

type Item = [string, string, string, string, string[], string[]?];
const groups: [CapabilityKind, Item[]][] = [
  [
    "tool",
    [
      [
        "网页搜索",
        "信息检索",
        "检索公开网页并整理可核验的来源。",
        "search",
        ["构造检索词", "整理搜索结果"],
      ],
      [
        "文件读取",
        "文件处理",
        "读取文件内容并提取关键段落。",
        "file-text",
        ["定位文件", "提取文本"],
      ],
      [
        "PDF解析",
        "文件处理",
        "解析 PDF 文档并提取文本结构。",
        "file-search",
        ["识别文档", "提取页面文本"],
      ],
      [
        "Python执行",
        "代码执行",
        "运行 Python 脚本处理计算任务。",
        "code",
        ["准备代码", "执行并收集结果"],
      ],
      [
        "SQL查询",
        "数据查询",
        "构造 SQL 查询并整理返回结果。",
        "database",
        ["生成查询", "整理数据"],
      ],
      ["表格计算", "数据处理", "对表格数据进行统计与计算。", "table", ["识别字段", "计算指标"]],
    ],
  ],
  [
    "skill",
    [
      [
        "需求分析",
        "产品设计",
        "梳理用户问题、范围与验收标准。",
        "target",
        ["明确业务目标", "识别用户场景", "拆解功能需求", "定义验收标准"],
      ],
      [
        "PRD编写",
        "产品设计",
        "将需求转化为结构化产品需求文档。",
        "clipboard",
        [
          "明确背景目标",
          "定义用户角色",
          "梳理业务流程",
          "拆分功能需求",
          "补充边界与异常",
          "整理验收标准",
        ],
      ],
      [
        "代码审查",
        "研发协作",
        "从正确性、可维护性与测试角度审查代码。",
        "code-review",
        ["理解变更范围", "检查逻辑正确性", "审查安全边界", "评估测试覆盖", "整理审查意见"],
      ],
      [
        "文档总结",
        "知识处理",
        "提炼长文档的结构、结论和行动项。",
        "document",
        ["识别文档结构", "提取关键结论", "整理摘要与行动项"],
      ],
      [
        "数据洞察",
        "数据分析",
        "围绕业务指标发现趋势、异常和可能原因。",
        "chart",
        ["定义分析问题", "检查数据口径", "观察趋势变化", "分析异常原因", "提出行动建议"],
      ],
      [
        "演示文稿",
        "内容创作",
        "根据受众和目标组织演示大纲。",
        "presentation",
        ["明确受众目标", "设计叙事结构", "规划页面内容", "检查表达与结论"],
      ],
    ],
  ],
  [
    "mcp",
    [
      [
        "知识中心MCP",
        "知识服务",
        "连接知识中心并模拟检索文档。",
        "book",
        ["建立模拟连接", "查询知识", "整理来源"],
        ["知识搜索", "文档详情", "目录浏览"],
      ],
      [
        "数据库MCP",
        "数据服务",
        "连接数据库并模拟查询数据。",
        "database",
        ["建立模拟连接", "查询数据", "整理结果"],
        ["表结构查询", "SQL查询"],
      ],
      [
        "文件系统MCP",
        "文件服务",
        "连接文件系统并模拟浏览与读取。",
        "folder",
        ["建立模拟连接", "定位文件", "整理结果"],
        ["目录列表", "文件读取"],
      ],
      [
        "浏览器MCP",
        "网页服务",
        "连接浏览器并模拟访问页面。",
        "globe",
        ["建立模拟连接", "浏览页面", "整理结果"],
        ["页面导航", "页面读取"],
      ],
      [
        "企业协作MCP",
        "协作服务",
        "连接协作平台并模拟查询团队信息。",
        "users",
        ["建立模拟连接", "查询信息", "整理结果"],
        ["成员查询", "文档查询"],
      ],
      [
        "任务中心MCP",
        "任务服务",
        "连接任务中心并模拟查看任务。",
        "list",
        ["建立模拟连接", "查询任务", "整理结果"],
        ["任务列表", "任务详情"],
      ],
    ],
  ],
  [
    "agent",
    [
      [
        "研究助手",
        "信息研究",
        "收集线索、比较资料并整理研究结论。",
        "compass",
        ["拆解研究问题", "收集资料", "归纳证据与结论"],
        ["网页搜索", "文件读取"],
      ],
      [
        "代码助手",
        "研发协作",
        "分析代码问题并规划修复和验证。",
        "terminal",
        ["理解代码问题", "定位相关文件", "提出修改与验证方案"],
        ["文件读取", "Python执行"],
      ],
      [
        "知识分析师",
        "知识分析",
        "综合知识资料，梳理主题与证据。",
        "brain",
        ["确定分析问题", "检索知识资料", "交叉分析并总结"],
        ["知识搜索", "文件读取"],
      ],
      [
        "数据分析师",
        "数据分析",
        "拆解指标、分析趋势并提出建议。",
        "bar-chart",
        ["定义分析指标", "查询与计算数据", "解释趋势并提出建议"],
        ["SQL查询", "表格计算"],
      ],
      [
        "文档专家",
        "文档处理",
        "整理文档结构并生成易读摘要。",
        "notebook",
        ["识别文档目标", "读取和归纳内容", "输出结构化文稿"],
        ["文件读取", "PDF解析"],
      ],
      [
        "任务规划师",
        "工作规划",
        "分解目标、安排步骤并识别依赖。",
        "calendar",
        ["澄清任务目标", "分解里程碑", "安排依赖与检查点"],
        ["任务列表", "网页搜索"],
      ],
    ],
  ],
];
export const capabilityCatalog: Capability[] = groups.flatMap(([kind, items]) =>
  items.map(([name, category, description, icon, steps, tools], index) => ({
    id: `${kind}-${index + 1}`,
    kind,
    name,
    category,
    description,
    icon,
    steps,
    source: "system" as const,
    ...(tools ? { tools } : {}),
  })),
);
export function getCapabilities(state: DemoState): Capability[] {
  return [...(state.catalog ?? capabilityCatalog), ...state.userSkills];
}
export function createInitialState(includeSeedConversations = true): DemoState {
  const now = "2026-01-01T09:00:00.000Z";
  const examples = [
    [
      "百万级文档混合检索架构",
      "如何设计百万级文档的混合检索？",
      "可以结合关键词检索与向量检索，通过融合排序和重排序提高召回质量；同时按租户隔离索引，并用离线评测集验证效果。",
    ],
    [
      "Agent工具权限设计",
      "如何控制智能体调用工具的权限？",
      "建议按用户身份、工具和资源分别授权，执行前做服务端校验，并记录调用参数与审计结果。",
    ],
    [
      "LangGraph状态管理",
      "如何管理多步骤工作流的状态？",
      "将共享状态定义为明确的结构，约定各节点的读写范围，并通过检查点支持中断恢复。",
    ],
    [
      "提示词管理后台",
      "提示词后台需要哪些功能？",
      "可先实现模板编辑、变量校验、版本管理和发布回滚，再加入测试集与效果对比。",
    ],
    [
      "Milvus索引优化",
      "向量检索索引如何优化？",
      "先衡量数据规模、召回率和延迟，再比较索引类型及参数，并以代表性查询进行压测。",
    ],
    [
      "聊天工作台UI设计",
      "聊天工作台应该如何组织？",
      "建议将会话导航、消息区域与输入区分层，保证窄屏适配、键盘操作及生成状态清晰可见。",
    ],
  ];
  return {
    version: 1,
    conversations: includeSeedConversations
      ? examples.map(([title, question, answer], i) => ({
          id: `conversation-${i + 1}`,
          title,
          createdAt: now,
          updatedAt: now,
          messages: [
            {
              id: `seed-${i + 1}-user`,
              role: "user" as const,
              content: question,
              status: "complete" as const,
            },
            {
              id: `seed-${i + 1}-assistant`,
              role: "assistant" as const,
              content: answer,
              status: "complete" as const,
            },
          ],
        }))
      : [],
    catalog: capabilityCatalog,
    favorites: ["tool-1", "skill-2", "agent-3"],
    userSkills: [],
    connectors: capabilityCatalog
      .filter((item) => item.kind === "mcp")
      .map((item, i) => ({
        id: item.id,
        name: item.name,
        url: `https://mcp-${i + 1}.example.invalid`,
        status:
          i === 0 || i === 2 || i === 5 ? "connected" : i === 3 ? "unauthorized" : "unconfigured",
      })),
    files: [
      { id: "file-1", name: "项目需求.md", type: "text/markdown", size: 2048, createdAt: now },
      { id: "file-2", name: "知识资料.pdf", type: "application/pdf", size: 512000, createdAt: now },
      { id: "file-3", name: "数据样例.csv", type: "text/csv", size: 8192, createdAt: now },
    ],
    draft: { text: "", capability: null, fileIds: [] },
    drafts: {},
    activeDraftKey: "new",
  };
}
