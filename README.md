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
