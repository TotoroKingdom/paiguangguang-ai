# V1 PRD：首页内容重构

> 状态：已实现并完成前端验证
> 范围：首页信息架构与内容重构
> 验证：6 项受影响首页测试、TypeScript 类型检查、lint 代码规范检查；1440 / 768 / 390 / 320 像素布局、键盘焦点、减少动态效果及 /rag 返回导航
> 分支：dev
> 目标仓库：TotoroKingdom/paiguangguang-ai

---

## 1. 背景

首页当前已采用浅色新拟态（light neumorphism）、空间感布局和 3D AI 视觉。下一阶段不重新设计视觉，而是调整内容结构，让招聘方在短时间内看清候选人的身份、工程能力、已完成成果和成长方向。

首页的主要定位是：

**AI Agent Engineer（AI 智能体工程师）**

全栈能力作为辅助能力呈现，职业方向继续朝向：

**AI Agent Architect（AI 智能体架构师）**

首页通过系统、项目和技术研究展示工程能力，不做传统简历页面。

---

## 2. 产品目标

首页需要围绕以下六个问题组织内容：

1. 这个人是谁？
2. 能构建什么系统？
3. 已经完成了什么？
4. 正在构建什么？
5. 正在研究哪些开源系统？
6. 职业方向如何发展？

主要访问者，尤其是招聘方和招聘经理，应能在一次短暂浏览中理解：

- 当前职业身份和主攻方向；
- 四项核心 AI 工程能力；
- 三个已完成的工程项目；
- 三个正在进行的项目；
- 对 Agent（智能体）运行框架和相关开源系统的研究；
- 从后端工程师成长为 AI 智能体架构师的路径。

---

## 3. 设计原则

### 3.1 保留现有视觉系统

本阶段必须保留当前已接受的视觉方向：

- 浅色新拟态；
- 空间感布局；
- 3D AI 元素；
- 柔和动效；
- 简洁、克制的 AI 产品气质。

不回退到以下风格：

- 深色赛博朋克；
- 黑客仪表盘；
- 终端堆叠；
- 强烈霓虹发光；
- 密集的技术 Logo 墙。

### 3.2 用证据说明能力

避免使用“精通 AI”“专家级 LangChain”“Python 90%”或“全栈 85%”等泛化口号和技能百分比。能力应通过具体的系统问题、工程链路和项目成果说明。

### 3.3 明确项目归属与状态

项目必须在视觉和语义上区分三种状态：

- **BUILT（已完成）**：已明确完成工程阶段的个人系统。完成表示工程工作已实现，不要求项目公开或部署。
- **BUILDING（在建）**：当前仍在开发或持续完善的个人系统。
- **EXPLORING（研究中）**：正在学习和分析的外部开源系统，不表示个人作者身份。

BUILT 项目只使用已确认的成果描述，不使用未经确认的质量等级标签或同类质量承诺。

### 3.4 中文优先

首页标题、说明和项目价值描述以中文为主。必要的英文技术词保留英文，并在首次出现时附带中文解释，例如 Agent（智能体）、Harness（运行框架）、RAG（检索增强生成）。

### 3.5 首页不是简历

不加入：

- 教育经历；
- 完整工作履历时间线；
- 技能进度条；
- 大量证书；
- GitHub 贡献热力图；
- 长篇自传。

首页表达工程能力和发展方向，不复刻简历。

---

## 4. 目标用户

### 4.1 主要用户：招聘方和招聘经理

他们需要快速了解：

- 候选人的当前定位；
- 实际 AI 工程能力；
- 项目完成情况和系统深度；
- 当前投入方向与职业成长。

### 4.2 次要用户：AI 工程师、架构师和潜在合作者

他们需要看到：

- 系统思维；
- Agent、知识系统和后端工程的结合方式；
- 正在研究的开源系统；
- 可产生合作的技术方向。

---

## 5. 首页信息架构

首页按以下顺序组织：

    HERO（首屏身份）
      ↓
    能力
      ↓
    作品 / BUILT（已完成）
      ↓
    作品 / BUILDING（在建）
      ↓
    研究 / EXPLORING（研究中的开源系统）
      ↓
    成长方向
      ↓
    联系

Hero（首屏）直接承担身份介绍，不再创建独立的 WHO I AM（关于我）区块，避免身份信息重复。作品导航先定位到 BUILT（已完成）区块，在建项目紧随其后。

---

# 6. 区块要求

## 6.1 Hero / 首屏身份

### 目标

首屏应立即回答：

- 这个人是谁？
- 主要是什么类型的工程师？
- 正在构建哪类系统？

### 内容

主身份：

**AI Agent Engineer（AI 智能体工程师）**

辅助身份：

**Full-stack Engineer（全栈工程师）**

中文主说明：

> 我专注于把 AI 能力做成可用的系统与产品。

方向关键词：

- AI Agent（AI 智能体）
- RAG / Knowledge Systems（检索增强生成 / 知识系统）
- AI Applications（AI 应用）
- Agent Harness / Runtime（智能体运行框架 / 运行时）

职业演进可简写为：

    Backend Engineer（后端工程师）
    → AI Application Engineer（AI 应用工程师）
    → AI Agent Engineer（AI 智能体工程师）
    → AI Agent Architect（AI 智能体架构师）

### 要求

- 保留当前 3D Hero 视觉和空间感布局；
- 身份、职业方向和中文说明在 Hero 内完成；
- 不在后续区块重复完整身份介绍；
- CTA（行动按钮）优先指向“作品”和 GitHub；
- 中文标题和说明优先，英文只作为身份或技术术语辅助。

## 6.2 能力 / Capabilities

### 目标

用系统能力说明工程价值，而不是罗列技术清单。

### 四项能力支柱

#### A. Agent 工程 / Agent Engineering

能力主题：

- LangGraph（有状态工作流）；
- 规划与执行循环；
- Tool Calling（工具调用）；
- Human-in-the-loop（人在回路）；
- Memory（记忆）；
- State Management（状态管理）；
- Verification / Evaluation（验证与评估）；
- Failure Recovery（失败恢复）。

核心说明：

> 能设计和实现可观察、有状态、可恢复的 Agent 工作流，而不只是调用一次模型。

#### B. RAG 与知识系统 / RAG & Knowledge Systems

能力主题：

- 文档摄取；
- 分块；
- Embedding（向量嵌入）；
- Hybrid Retrieval（混合检索）；
- RRF（倒数排名融合）；
- Rerank（重排序）；
- 上下文组装；
- 引用与来源追踪；
- 权限过滤；
- 评估。

核心说明：

> 能构建完整的知识检索链路，让来源可追踪、上下文可控制、访问边界可管理。

#### C. 后端与 AI 基础设施 / Backend & AI Infrastructure

能力主题：

- Java 后端；
- Python / FastAPI；
- Redis；
- PostgreSQL；
- 向量数据库；
- Docker；
- CI/CD（持续集成与持续交付）；
- 可观测性；
- API 与服务设计。

核心说明：

> 能为 AI 系统提供可靠的应用、数据和基础设施基础。

#### D. AI 产品工程 / AI Product Engineering

能力主题：

- Next.js；
- AI UX（AI 用户体验）；
- 流式交互；
- Agent UI（智能体界面）；
- 模型与供应商集成；
- Vibe Coding 工作流；
- 产品交付。

核心说明：

> 能把 AI 能力转化为可使用的产品，而不是停留在孤立的演示。

### 要求

- 不使用技能百分比；
- 框架和工具只作为能力证据；
- 每张能力卡保持简洁、可扫描；
- 能力描述优先说明问题、系统和结果。

## 6.3 作品 / BUILT（已完成）

### 目标

提供已确认工程能力的具体证据。

以下三个项目均已达到明确的工程阶段，视为已完成项目。BUILT 只说明工程实现已完成，不表示项目必须公开、部署或对外提供服务。

每张卡包含：

- 项目名称；
- 中文为主的一句话定位；
- 解决的问题或用途；
- 关键工程能力；
- BUILT（已完成）状态；
- 只有在存在真实入口时才提供链接。

### 项目 1：RAG 系统

定位：**KNOWLEDGE（知识）**

标题：**RAG 系统**

核心链路：

    文档摄取
    → 分块
    → 向量嵌入
    → 混合检索
    → RRF
    → 重排序
    → 上下文组装
    → 引用
    → 评估

能力证据：

- 检索工程；
- 上下文质量；
- 来源可追踪；
- 检索评估。

链接：

- 保留真实入口：/rag；
- CTA：查看系统 →。

### 项目 2：AI Chatbot（AI 聊天机器人）

定位：**CONVERSATION（对话）**

标题：**AI Chatbot（AI 聊天机器人）**

能力主题：

- 多会话管理；
- 持久化历史；
- 流式响应；
- 短期记忆；
- 长期记忆；
- 语义记忆；
- Checkpoint（检查点）；
- Redis；
- PostgreSQL；
- LLM Gateway（大语言模型网关）与供应商抽象。

能力证据：

- 对话基础设施；
- 记忆架构；
- 数据持久化；
- 可持续的聊天流程。

链接：

- 当前没有确认的公开或详情页入口时，只展示内容，不创建假链接。

### 项目 3：Office Automation Agent（办公自动化智能体）

定位：**ACTION（行动）**

标题：**Office Automation Agent（办公自动化智能体）**

能力主题：

- Agent 工作流；
- Tool Calling（工具调用）；
- Human-in-the-loop（人在回路）；
- 审批；
- 业务 API 集成；
- 结构化输出；
- 审计记录。

能力证据：

- Agent 行动；
- 企业流程；
- 工具集成；
- 受控执行。

链接：

- 当前没有确认的公开或详情页入口时，只展示内容，不创建假链接。

### 已完成项目叙事

三个项目共同表达一条系统能力链：

    KNOWLEDGE（知识）       RAG 系统
    CONVERSATION（对话）    AI Chatbot
    ACTION（行动）          Office Automation Agent

不使用未经确认的质量等级标签或部署承诺。

## 6.4 作品 / BUILDING（在建）

### 目标

展示当前正在投入的技术方向。这些项目不是已完成作品，必须明确显示 BUILDING（在建）状态。

### 项目 1：Knowledge Platform（知识平台）

定位：**Knowledge Platform（知识平台）**

关注方向：

- 知识治理；
- 知识对象；
- ACL / 权限；
- 治理规则；
- Agent 治理；
- 企业知识基础设施。

说明：

> 正在构建可被 Agent 安全使用的企业知识基础设施。

### 项目 2：Enterprise Digital Employee（企业数字员工）

定位：**Enterprise Digital Employee（企业数字员工）**

关注方向：

- Agent 运行时；
- 企业工具；
- 工作流编排；
- Human-in-the-loop（人在回路）；
- 企业系统集成；
- 审批与审计；
- 任务执行。

说明：

> 正在探索 Agent 如何在企业工作流中执行受控、可审计的工作。

### 项目 3：ChatGPT Harness（ChatGPT 运行框架）

定位：**ChatGPT Harness（ChatGPT 运行框架）**

关注方向：

- 模型运行框架；
- Agent 运行时；
- 工具协议；
- 记忆；
- 上下文工程；
- 执行环境；
- 开发者体验。

说明：

> 正在构建围绕模型、工具、上下文和 Agent 执行的可控运行框架。

### 要求

- 三个项目都显示 BUILDING（在建）；
- 不把在建项目描述为完成成果；
- 没有真实公开入口时只展示描述；
- 不添加未经确认的质量等级或交付承诺；
- 在建区紧跟 BUILT 区，作品导航默认先定位到 BUILT。

## 6.5 研究 / EXPLORING（研究中的开源系统）

### 目标

展示当前正在学习和分析的外部开源系统，明确区分个人项目和外部项目。

区块主标题：**研究中的开源系统**

辅助说明：

> 通过研究运行框架、工具执行、上下文、记忆和系统集成，持续理解 Agent 系统如何工作。

### 研究项目与官方仓库

| 研究对象 | 官方仓库 | 研究主题 |
|---|---|---|
| Codex | [openai/codex](https://github.com/openai/codex) | Agent Harness（智能体运行框架）、工具执行、上下文工程、开发者集成 |
| DeepSeek Harness | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | Agent 运行框架、工具执行、上下文与记忆、系统集成 |
| Pi | [earendil-works/pi](https://github.com/earendil-works/pi) | 运行时、工具执行、上下文工程、Agent 集成 |
| Hermes | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Agent 架构、工具、记忆和集成 |
| OpenClaw | [openclaw/openclaw](https://github.com/openclaw/openclaw) | Agent 集成、工具执行、上下文与记忆 |
| PyTorch 学习实践 | [mrdbourke/pytorch-deep-learning](https://github.com/mrdbourke/pytorch-deep-learning) | Daniel Bourke 的课程与深度学习实践 |

DeepSeek Harness 指上表中的官方上游仓库，不是 DeepSeek 模型。旧的 TotoroKingdom/deepseek-harness 是该仓库的 fork（分叉），不作为研究卡片目标。

旧的 Mini-Codex 卡片和个人 fork DeepSeek Harness 卡片均移除。研究区只表达“研究中”，不表达对外部仓库的作者身份。

### 卡片与交互

每张卡包含：

- 项目名称；
- 来源组织或作者；
- 一句研究理由；
- 2–4 个研究主题；
- 外部链接标识。

整张卡使用语义链接，点击后在新标签页打开对应官方仓库。研究仓库链接必须存在且使用上表中的官方地址；不猜测或替换为个人仓库。

## 6.6 成长方向 / Career Journey

### 目标

展示能力演进，而不是完整履历时间线。

### 路径

    Backend Engineer（后端工程师）
    可靠的应用与服务工程
            ↓
    AI Application Engineer（AI 应用工程师）
    RAG · LLM · AI 产品
            ↓
    AI Agent Engineer（AI 智能体工程师）【当前】
    工作流 · 工具 · 记忆 · 人在回路
            ↓
    AI Agent Architect（AI 智能体架构师）【目标】
    Agent 运行时 · 知识基础设施
    分布式 Agent 系统 · 评估 · 治理

### 要求

- 当前阶段突出显示：AI Agent Engineer（AI 智能体工程师）；
- 目标阶段明确显示：AI Agent Architect（AI 智能体架构师）；
- 不使用具体年份；
- 不重复完整就业经历；
- 重点说明能力如何从后端、AI 应用发展到 Agent 架构。

---

# 7. 联系区

底部保留简洁的联系 CTA。

至少包含：

- GitHub；
- Email（邮箱）。

联系方式沿用现有 GitHub 和邮箱。简历、LinkedIn 等链接可以作为未来扩展，但不改变首页主叙事。

---

# 8. 导航

导航采用紧凑的中文名称：

    关于
    作品
    研究
    成长
    GitHub ↗

锚点要求：

- 关于：定位到 Hero 首屏身份；
- 作品：定位到 BUILT（已完成）区，BUILDING（在建）区紧随其后；
- 研究：定位到研究中的开源系统；
- 成长：定位到职业成长路径；
- GitHub：打开现有 GitHub 链接。

导航不显示“能力、已完成、在建”等过多顶级项目，避免视觉拥挤。共享导航在 /rag 页面也应能返回首页对应栏目。

---

# 9. 内容模型

首页内容应集中管理，避免在组件中重复硬编码。建议保留以下逻辑实体：

    Identity
    Capability
    CompletedProject
    ActiveProject
    ExplorationProject
    CareerStage

接口要求：

- Identity 由 Hero 使用，不单独渲染重复的身份区；
- CompletedProject 和 ActiveProject 的个人项目链接可选；
- ExplorationProject 的官方仓库链接必填；
- RAG 项目保留 /rag 链路；
- AI Chatbot、Office Automation Agent 和在建项目没有真实入口时，不生成假链接或空详情页；
- 状态字段应支持 BUILT、BUILDING、EXPLORING；
- 内容集中管理，便于更新项目状态、研究链接和职业阶段。

本 PRD 不规定具体 TypeScript 类型字段，也不要求新增后端接口。

---

# 10. 组件方向

现有首页结构可以在不重写整个前端架构的前提下演进。建议方向：

    homepage-hero.tsx
    homepage-capabilities.tsx
    homepage-built.tsx
    homepage-building.tsx
    homepage-exploring.tsx
    homepage-journey.tsx
    homepage-contact.tsx

已有组件可按实际情况复用或重命名：

    HomepageOverview
    → HomepageCapabilities

    HomepageProjects
    → HomepageBuilt
       + HomepageBuilding
       + HomepageExploring

    HomepageRoadmap
    → HomepageJourney

不要新增独立的 homepage-identity.tsx 来重复 Hero 身份。具体组件拆分属于实现任务，不扩展本 PRD 的范围。

---

# 11. 非目标

本阶段不包括：

- 重新设计已接受的新拟态视觉；
- 替换当前 Hero 3D 系统；
- 后端改动；
- 认证改动；
- API 重设计；
- RAG 系统功能实现；
- Agent 功能改动；
- 详情页重设计；
- 新增外部服务；
- 新增 CMS；
- 重写整个网站架构。

后端和现有详情页保持不变；本轮只调整首页内容、结构、导航及其直接受影响的前端测试。

---

# 12. 响应式要求

新内容结构必须适配：

- 桌面端；
- 平板端；
- 移动端。

移动端要求：

- 保持相同的语义顺序；
- BUILT、BUILDING、EXPLORING 状态标签持续可见；
- 外部开源卡片清楚标记外部链接；
- 成长路径可从横向改为纵向；
- 能力卡片可自然堆叠；
- 任何重要内容不能只依赖 hover（悬停）交互。

---

# 13. 无障碍要求

- 外部链接必须可识别；
- 可点击卡片必须使用语义链接并支持键盘访问；
- 焦点状态保持可见；
- 内容含义不能只依赖颜色；
- 动效遵守 prefers-reduced-motion（减少动态效果）；
- 标题层级有效；
- 新标签页打开外部仓库时提供明确的外部链接语义。

---

# 14. 成功标准

访问者浏览首页后可以回答：

1. 这位工程师是谁？
2. 他能构建什么系统？
3. 他已经完成了什么？
4. 他正在构建什么？
5. 他正在研究哪些外部开源系统？
6. 他正在朝什么职业方向发展？

其他验收信号：

- BUILT、BUILDING、EXPLORING 三种状态视觉上明确区分；
- 首页不呈现为传统简历模板；
- 当前新拟态和 3D Hero 视觉仍可识别；
- 技术内容简洁但可信；
- 项目链接只指向已确认的真实入口；
- 外部开源项目不会被误认为个人作品；
- 中文为主，必要英文术语有中文解释；
- 招聘方能快速读出 AI Agent Engineer 主身份、全栈辅助能力和已完成项目证据。

---

# 15. 验收清单

## 信息架构

- [x] Hero 首屏直接表达 AI Agent Engineer 主身份和中文说明。
- [x] 不存在重复的独立 WHO I AM 身份区。
- [x] 能力区包含四项能力支柱。
- [x] BUILT 区包含 RAG、AI Chatbot、Office Automation Agent。
- [x] BUILDING 区包含 Knowledge Platform、Enterprise Digital Employee、ChatGPT Harness。
- [x] 研究区包含六个指定的外部开源系统。
- [x] 成长路径以 AI Agent Architect 为目标。
- [x] 联系区保留 GitHub 和邮箱。

## 归属与状态

- [x] 三个已完成项目均标记 BUILT（已完成）。
- [x] 三个在建项目均标记 BUILDING（在建）。
- [x] 研究项目均明确是外部开源系统并标记 EXPLORING（研究中）。
- [x] RAG 链接为 /rag。
- [x] 没有真实入口的个人项目只展示内容，不出现假链接。
- [x] 外部仓库使用官方链接并在新标签页打开。
- [x] Mini-Codex 和个人 fork DeepSeek Harness 卡片已移除。
- [x] 不使用未经确认的质量等级标签或交付承诺。

## 内容质量

- [x] 没有技能百分比条。
- [x] 没有密集技术 Logo 墙。
- [x] 没有长篇简历式自传。
- [x] 能力以工程问题、系统和结果描述。
- [x] 项目文案说明系统能力和用途，不夸大状态。
- [x] PyTorch 项明确写为 Daniel Bourke 的课程与实践学习。

## 导航、视觉与可访问性

- [x] 导航只保留“关于、作品、研究、成长、GitHub”。
- [x] 作品入口先到 BUILT，BUILDING 紧随其后。
- [x] /rag 页面共享导航可返回首页栏目。
- [x] 现有浅色新拟态设计语言保持不变。
- [x] 现有 3D Hero 方向保持不变。
- [x] 桌面、平板、移动端层级清晰。
- [x] 键盘访问、焦点、标题层级和减少动态效果符合要求。

---

# 16. 已确认决定

本节替代原开放问题，以下决定已在实施前确认：

1. **身份定位**：中文为主，主身份为 AI Agent Engineer（AI 智能体工程师）；Full-stack Engineer（全栈工程师）作为辅助能力。身份介绍全部合并到 Hero，不新增重复身份区。
2. **首页顺序**：Hero → 能力 → BUILT → BUILDING → 研究 → 成长 → 联系。
3. **已完成项目**：仅展示 RAG、AI Chatbot、Office Automation Agent。三项能力均已真实实现，BUILT 只表示工程阶段完成，不要求项目公开或部署。
4. **已完成命名**：删除未经确认的质量等级命名或承诺，改为事实性的系统和能力描述。
5. **在建项目**：展示 Knowledge Platform、Enterprise Digital Employee、ChatGPT Harness 三个描述性名称，并显著标记 BUILDING。
6. **旧卡片处理**：移除 Mini-Codex 和个人 fork 的 DeepSeek Harness 卡片。DeepSeek Harness 研究卡片只使用官方上游仓库，且明确它不是 DeepSeek 模型。
7. **链接策略**：RAG 保留 /rag；AI Chatbot、Office Automation Agent 和在建项目没有真实入口时只展示内容，不生成假链接或详情页。
8. **研究仓库**：固定使用以下官方链接：
   - [openai/codex](https://github.com/openai/codex)
   - [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)
   - [earendil-works/pi](https://github.com/earendil-works/pi)
   - [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
   - [openclaw/openclaw](https://github.com/openclaw/openclaw)
   - [mrdbourke/pytorch-deep-learning](https://github.com/mrdbourke/pytorch-deep-learning)
9. **研究主题**：研究文案围绕运行框架、工具执行、上下文、记忆和集成；PyTorch 项明确为 Daniel Bourke 的课程与实践学习。
10. **导航**：采用“关于、作品、研究、成长、GitHub”；作品定位到已完成区，在建区紧随其后。
11. **职业路径**：Backend Engineer → AI Application Engineer → AI Agent Engineer（当前）→ AI Agent Architect（目标）。
12. **范围**：保留现有浅色新拟态和 3D Hero；后端和详情页不改；维持一个前端实现任务；不新增 PRD 以外的文档。

---

# 17. 产品叙事

首页应当读起来像一条连续的工程成长故事：

    我是一名 AI Agent Engineer（AI 智能体工程师）
            ↓
    我能构建知识、对话和行动系统
            ↓
    这些是我已经完成的三个工程项目
            ↓
    这些是我正在构建的企业知识、数字员工和运行框架
            ↓
    这些是影响我思考方式的开源系统
            ↓
    我正在成长为 AI Agent Architect（AI 智能体架构师）

实现时以这条叙事为内容取舍标准：优先让招聘方看到身份、工程证据和成长方向，再提供技术研究细节。

---

# 18. 执行模式

本 V1 保持轻量，所有决定已在第 16 节确认。

不要为本次改动创建单独的 ARCHITECTURE、ROADMAP、SPEC、PLAN 或 TASKS 文档。实现作为一个前端重构任务完成，范围包括：

1. 首页信息架构重组；
2. 能力与集中内容数据更新；
3. BUILT / BUILDING / EXPLORING 项目分组；
4. 成长路径重构；
5. 导航和内容链接更新；
6. 因新结构直接产生的响应式与无障碍调整；
7. 受影响的首页测试、TypeScript 类型检查和 lint 检查。

现有视觉设计系统、Hero 3D 方向、后端、详情页和其他页面功能均不在本次重构范围内。
