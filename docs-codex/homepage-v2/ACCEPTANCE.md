# 首页 V2 与智能助手验收记录

日期：2026-11-05。分支：`codex/homepage-v2`。本记录为本地实现与验证证据，不代表用户已签收或生产发布。

## 实现结果

首页四组能力及 LangGraph 二级模式完整对齐 V2；智能助手整卡可访问 `/assistant`；知识中心、五个探索项目、四阶段职业规划已调整。首屏、六个导航锚点和三维场景保留。

助手已实现聊天首页、工具、技能、MCP 连接器、智能体、文件库及 `/assistant/chat/[id]`。包括能力搜索/分类/详情/常用、Markdown 技能导入、模拟连接配置与失败重试、文件元信息上传和多附件、逐段模拟输出/停止/逐消息重试、会话管理、按会话隔离草稿、刷新恢复、异常存储降级和确认重置。

## 自动验证

| 检查 | 实际结果 |
| --- | --- |
| 实施前 `npm test` | 7 个文件、39 项通过 |
| 最终 `npm test -- --reporter=dot` | 13 个文件、70 项通过 |
| 最终 `npm run lint` | 无 ESLint 警告或错误 |
| 最终 `npm run build` | 编译、类型检查、页面生成、构建追踪通过；新增助手静态页面及动态会话路由均成功 |
| 完整 `npm run test:e2e` | 桌面 15 项 + 手机视口 15 项，共 30 项通过（系统 Chrome 无界面模式） |
| 无环境变量 `npm run test:e2e -- --grep "capture desktop"` | 2 项通过，验证自动浏览器回退及完整截图采集 |
| `git diff --check` | 通过 |
| 手机首页额外几何检查 | 视口 390，页面宽 390；能力区说明左 20、右 370、宽与 scrollWidth 均 350，无横向溢出；三维场景状态 `ready` |

浏览器完整套件覆盖：首页内容和整卡键盘入口、RAG 页面保留、所有助手页面直达/刷新/前后退、四类能力聊天、分类和常用、@ 搜索、技能导入/正文/删除、MCP 未连接拦截/地址校验/失败/重试/断开、文件元信息与多附件/删除后历史快照、停止/恢复/失败重试不重复用户消息、会话草稿隔离、搜索/重命名/删除、缺失及 constructor/toString 路由、损坏和不可用存储、确认重置、弹窗和移动侧栏键盘焦点、内容与输入区边界、减少动态效果及首页双向滚动。所有场景同时检查浏览器运行时错误和外部 HTTP 请求，均无异常。

测试环境：桌面 1440 × 1000；手机为 Chrome 的 390 × 844 视口模拟，非实体手机。使用本地 Next.js 开发服务进行浏览器测试，生产构建另行执行。Playwright 下载较慢，因此本机使用已安装 Chrome；配置优先使用 Playwright Chromium，在 Windows 未安装该浏览器而存在 Chrome 时自动回退。

## 复现命令

在 `E:\paiguangguang-ai\frontend` 执行：

```powershell
npm ci
npm test
npm run lint
npm run build
npm run test:e2e
```

没有可用测试浏览器时先执行 `npx playwright install chromium`。可用 `PLAYWRIGHT_CHANNEL` 显式选择已安装的浏览器通道。测试自动使用 3100 端口启动服务；需要手动截图时执行 `npm run test:e2e -- --grep "capture desktop"`。

## 截图与目视核对

共 26 张 PNG，约 2.87 MiB。以下是 Playwright 生成的实际截图。目视核对由 Agent 查看图像完成，与自动交互测试分别记录；不等同于实体设备测试或用户签收。

| 页面 / 状态 | 桌面 | 手机视口 |
| --- | --- | --- |
| 首屏与正常三维场景 | [桌面](screenshots/desktop-home-hero-normal.png) | [手机](screenshots/mobile-home-hero-normal.png) |
| 能力区与三维构图 | [桌面](screenshots/desktop-home-capabilities.png) | [手机](screenshots/mobile-home-capabilities.png) |
| 四组能力完整长图 | [桌面](screenshots/desktop-home-capabilities-full.png) | [手机](screenshots/mobile-home-capabilities-full.png) |
| 作品区 | [桌面](screenshots/desktop-home-projects.png) | [手机](screenshots/mobile-home-projects.png) |
| 智能助手作品卡 | [桌面](screenshots/desktop-home-assistant-card.png) | [手机](screenshots/mobile-home-assistant-card.png) |
| 职业规划 | [桌面](screenshots/desktop-home-journey.png) | [手机](screenshots/mobile-home-journey.png) |
| 助手初始页 | [桌面](screenshots/desktop-assistant-initial.png) | [手机](screenshots/mobile-assistant-initial.png) |
| 工具库 | [桌面](screenshots/desktop-assistant-tools.png) | [手机](screenshots/mobile-assistant-tools.png) |
| 技能库 | [桌面](screenshots/desktop-assistant-skills.png) | [手机](screenshots/mobile-assistant-skills.png) |
| 连接器中心 | [桌面](screenshots/desktop-assistant-mcp.png) | [手机](screenshots/mobile-assistant-mcp.png) |
| 智能体中心 | [桌面](screenshots/desktop-assistant-agents.png) | [手机](screenshots/mobile-assistant-agents.png) |
| 文件库 | [桌面](screenshots/desktop-assistant-files.png) | [手机](screenshots/mobile-assistant-files.png) |
| 技能聊天与完整步骤 | [桌面](screenshots/desktop-assistant-chat.png) | [手机](screenshots/mobile-assistant-chat.png) |

实际目视结果：首页保留原有首屏与三维视觉，桌面四组能力为双列，LangGraph 子层级完整；手机为单列。助手初始页、工具/技能/MCP/智能体/文件库与聊天的卡片、按钮和输入区未见必须修复的明显遮挡、截断或错位。长列表在输入框上方的独立区域滚动。能力区长截图贴边来自按 section 边界裁切，额外 DOM 几何检查确认页面与说明文字未溢出。

## 本地审阅

已启动仅监听本机的开发预览：
- 首页：http://127.0.0.1:3100/
- 助手：http://127.0.0.1:3100/assistant

重启可在前端目录运行 `npm run dev -- --hostname 127.0.0.1 --port 3100`。

## 范围限制

所有聊天、工具执行、连接状态和任务过程均为模拟；文件只保存元信息，不解析正文。数据仅保留在当前浏览器。未接入真实模型、权限系统或业务后端，未进行生产发布。后端未修改。本地代码尚未 Git 提交或推送。
