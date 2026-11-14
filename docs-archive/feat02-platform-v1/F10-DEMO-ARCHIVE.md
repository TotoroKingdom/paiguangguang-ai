# feat02 F10 存量 Demo 归档

## 1. 行为

当 `ASSISTANT_DEMO_CATALOG_ENABLED=false` 时，服务启动会扫描来源为 `demo` 且尚未停用的能力定义：

- 将能力定义状态改为 `disabled`。
- 保留全部定义、版本、依赖、Run 和历史引用。
- 为每个能力写入 `capability.demo.archived` 系统审计事件。
- 重复启动幂等，不会重复归档或重复写审计。
- 非 Demo 能力不受影响。

该行为只归档，不执行删除、清空或重写历史。

## 2. 生效边界

- 开发环境默认 `demo_catalog_enabled=true`，不触发归档。
- 生产环境已被配置校验强制要求 `demo_catalog_enabled=false`，因此部署新版本后首次启动会归档存量 Demo。
- 本地自动化已验证状态、版本保留、非 Demo 隔离和幂等审计。
- 尚未在生产数据库执行，实际生产行数与审计结果仍属于 F16/F17 生产核验。

## 3. 证据层级

- L1 自动化：`backend/tests/test_demo_archive.py`。
- 生产执行：**NOT_RUN**。
