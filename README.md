```mermaid
flowchart TD

    A["PRD + ARCHITECTURE + ROADMAP"]
    B["SPEC"]
    C["PLAN"]
    D["TASKS"]

    E["Integration Test Plan"]
    F["E2E Test Plan"]
    G["Manual Acceptance Checklist"]

    H["Development"]
    I["Unit Tests"]
    J["Integration Tests"]
    K["E2E Tests"]
    L["Manual Acceptance"]
    M["ACCEPTED / FROZEN"]

    A --> B
    B --> C
    C --> D

    D --> E
    D --> F
    D --> G

    E --> H
    F --> H
    G --> H

    H --> I
    I --> J
    J --> K
    K --> L
    L --> M
```

## 智能助手 V1

- 用户工作台：`/assistant`
- 管理控制台：`/assistant/admin`
- 管理员登录：`/assistant/admin/login`

架构、数据模型、API 与安全边界见
[`docs-archive/assistant-capability-console-v1/SPEC.md`](docs-archive/assistant-capability-console-v1/SPEC.md)。
管理员初始化、生产环境变量与迁移步骤见
[`docs-archive/assistant-capability-console-v1/DEPLOYMENT.md`](docs-archive/assistant-capability-console-v1/DEPLOYMENT.md)。
