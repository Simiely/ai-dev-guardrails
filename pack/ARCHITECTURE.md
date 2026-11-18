# 架构契约

> 本文件是给人看的视图；机器源是 `guardrails.yaml`。
> AI 不得修改本文件、`guardrails.yaml`、`adr/**`、`manual/**`、CI 配置；改动需 ADR + 人批。

## 1. 系统一句话

<这个系统是什么，为谁解决什么问题>

## 2. 模块与依赖方向

| 模块 | 层 | 职责 | 允许依赖 |
|---|---|---|---|
| `<order>` | `application` | `<...>` | `<payment>` |
| `<payment>` | `application` | `<...>` | `<domain>` |

依赖方向（只允许从左到右）：

```
domain  ←  application  ←  adapter
```

禁止：

- 反向依赖
- 循环依赖
- 跨模块 import 内部文件（只能 import 对方的 `CONTRACT`）

## 3. 公共契约

| 契约 | 位置 | 类型 | 消费者 |
|---|---|---|---|
| `<http.order>` | `<openapi/order.yaml>` | `openapi` | `<web, mobile>` |

修改任一契约 = R3 = ADR + 人批 + 契约快照 diff。

## 4. 数据与安全边界

- 可访问的数据：
- 禁止访问的数据：
- 密钥与凭据：
- 外部调用白名单：

## 5. 质量底线

- 新增或修改的代码必须有测试。
- 主流程必须有端到端或 holdout 验收。
- 错误必须可观测（日志 / 指标 / 追踪）。
- 不允许吞异常。
- 不允许用 ignore 注释绕过检查。

## 6. 禁止清单

- 不得新增未登记依赖。
- 不得修改 `manual/**`、`guardrails.yaml`、`adr/**`、CI 配置。
- 不得跨模块 import 内部文件。
- 不得自动批准 shell 或破坏性命令。

## 7. 验证命令

| 用途 | 命令 |
|---|---|
| 受影响测试 | `<command>` |
| 全量测试 | `<command>` |
| 类型检查 | `<command>` |
| lint | `<command>` |
| 架构规则 | `guardrails sync --check` |
| 契约检查 | `guardrails contract diff --base <snapshot> --current <path>` |

## 8. 变更记录

| 日期 | 变更 | ADR |
|---|---|---|
| | | |
