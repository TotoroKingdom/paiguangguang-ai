# RAG 页面改版验收记录

## 范围

- 将 `/rag` 接入首页的浅色 Soft Spatial（软空间）外壳与统一导航。
- 将原深色大卡片内的链路图改为全宽三段式架构：离线索引、在线检索、生成与回流。
- 增加“数据更新回环”和“质量反馈回环”，并区分数据流、权限约束与治理回环。
- 按节点职责区分卡片形态、图标、内部结构、强调色与字段标签。

## 自动验证

在 `frontend/` 下执行：

| 命令 | 结果 |
| --- | --- |
| `npm test` | PASS，21 个测试文件 / 85 个用例 |
| `npm run lint` | PASS |
| `npm run build` | PASS，`/rag` 作为静态页面生成 |

## 浏览器复核

- 桌面：1440 × 900，生产构建，确认统一导航、全宽链路、两条回环、卡片差异与页脚对齐。
- 窄屏：390 × 844，确认卡片单列顺序、连线方向、无横向溢出（`scrollWidth` 未超过视口）。
- 减少动态效果：样式包含 `prefers-reduced-motion: reduce` 与 `hover: none` 分支，禁用位移和过渡。
- 导航锚点：RAG 页复用首页 6 项导航，链接分别指向 `/#hero`、`/#capabilities`、`/#projects`、`/#building`、`/#exploring`、`/#journey`。

## 截图

- `screenshots/rag-desktop-top.png`
- `screenshots/rag-desktop-flow.png`
- `screenshots/rag-desktop-loop.png`
- `screenshots/rag-mobile-top.png`
- `screenshots/rag-mobile-cards.png`

以上为本地自动验证与浏览器视觉复核结果，不代表已部署生产环境或已完成人工验收。
