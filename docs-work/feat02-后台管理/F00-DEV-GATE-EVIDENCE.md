# feat02 / F00 开发环境门禁证据（SQLite 独立副本与迁移演练）

> 日期：2026-11-08（Asia/Shanghai）
> 分支：`feat/feat02-platform-v1`（从 `dev` `fd7f40b` 建立）
> 性质：**本地开发环境证据，不是生产验收**。
> 结论：开发环境 F00 的备份/恢复/迁移证据已补齐；**生产环境仍为 NOT_VERIFIED，生产门禁不得视为通过**。

## 1. 执行边界

- 源库：`C:\AI\paiguangguang-ai\.env\assistant.db`，仅以 `mode=ro` + `PRAGMA query_only=ON` 打开。
- 所有快照、恢复库、迁移库均位于独立目录 `C:\AI\paiguangguang-ai-feat02\.local-evidence\`，该目录已加入 `.gitignore`。
- 未修改源库、未执行 `stamp` 以外的历史改写，未触碰生产。
- 工具：`backend/scripts/f00_recovery_drill.py`（使用 SQLite backup API）。

## 2. 快照与完整性

| 项目 | 结果 |
|---|---|
| 快照大小 | 204,800 bytes |
| SHA-256 | `429e0ffd29a4bcb984b029d5aa5223a6999b2d405d625255dfd302ef26648dde` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | 0 条违规 |
| SQLite 版本 | 3.53.1 |
| `user_version` | 0 |
| `alembic_version` | 不存在（该库由 `create_all()` 创建） |

脱敏计数：

| 表 | 行数 |
|---|---:|
| `conversations` | 9 |
| `messages` | 4 |
| `admin_users` | 1 |
| `admin_sessions` | 2 |
| `capability_definitions` | 24 |
| `capability_versions` | 24 |
| `capability_dependencies` | 0 |
| `capability_runs` | 0 |
| `audit_events` | 4 |

孤儿消息：0；Owner 分桶：1 个 Owner 有 1 条会话，另一个 Owner 有 8 条会话。

## 3. 恢复演练

从快照再次通过 SQLite backup API 生成 `restored.db`：

- SHA-256 与快照完全一致。
- `integrity_check` 为 `ok`。
- 表计数、Schema、Owner 分桶、孤儿消息数全部一致。

**恢复一致性：PASS（本地副本范围内）。**

## 4. 旧 Schema 与 Alembic `0002` 差异

使用全新临时库执行 `alembic upgrade 0002_admin_capabilities` 后对比：

- 业务列完全一致。
- 差异仅为：
  - 旧库没有 `alembic_version`；
  - `admin_users.username` 在旧库中只有一个隐式唯一索引，迁移链生成的库多一个等价的唯一约束自动索引。
- 没有缺失或类型不一致的业务列。

因此仅在隔离副本上执行 `alembic stamp 0002_admin_capabilities`，再运行 `upgrade head`；没有对源库 stamp。

## 5. 旧库向前迁移

在隔离副本上执行 `0002 -> 0003 -> 0004 -> 0005 -> 0006 -> 0007 -> 0008`：

| 核对项 | 迁移前 | 迁移后 |
|---|---:|---:|
| `conversations` | 9 | 9 |
| `messages` | 4 | 4 |
| `admin_users` | 1 | 1 |
| 统一管理员账号 | — | `1` |
| 统一管理员角色/状态 | — | `ADMIN` / `ACTIVE` |
| 旧管理员密码摘要 | — | 与 `admin_users.password_hash` **逐字相同** |
| `admin_user_links` | 0 | 1 |
| `users` | 0 | 1 |

回退演练：`alembic downgrade 0002_admin_capabilities` 后 `integrity_check=ok`，`conversations=9`、`messages=4`、`admin_users=1` 保持不变。代码回退路径为恢复迁移前快照；本演练已验证快照与恢复库字节一致。

## 6. 全新迁移链

全新临时库：

- `upgrade head`：`0001 → 0008_runtime_runs` 全部成功。
- `downgrade base`：全部成功。
- 再次 `upgrade head`：成功，`integrity_check=ok`。

## 7. 仍未验证

- 生产数据库 revision、表计数、Owner 分布、管理员数量。
- 生产备份文件存在性、校验、恢复与保留策略。
- 生产旧管理员实际登录（本轮只能证明摘要格式与复制一致性，不知道真实密码）。
- 生产 TLS、443、Secure Cookie、Origin、部署权限、依赖风险。

以上均保持 **NOT_VERIFIED / BLOCKED**，不得以本地结果替代。
