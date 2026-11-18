---
id: card
title: 项目说明书
always: true
version: 1
---
# 项目说明书

## 目标

<一句话：这个项目是什么，为谁解决什么问题。>

## 红线

1. 不得修改 `ARCHITECTURE.md`、`guardrails.yaml`、`adr/**`、`manual/**`、`specs/<id>/raw/**`、CI 配置；改动需 ADR + 人批。
2. 不得跨模块 import 内部文件；只能 import 对方的 `CONTRACT`。
3. 不得在失败测试确认前修改源码。
4. 不得在 red 确认后修改测试；测试改动需 `test-change` 批准并重新 red。
5. 不得用 `@ts-ignore`、`eslint-disable`、`noqa`、`allow(...)` 绕过检查。
6. 不得删除、跳过测试，或修改断言迁就实现。
7. 不得新增依赖或模块而没有 ADR + 人批。
8. 不得扩大改动面；发现的问题写进 `findings.md`。
9. 不得在同一个问题失败两次后继续重试；停下来写清根因和三个方案。
10. 不得自动批准 shell；破坏性命令一律拒绝。
11. 摘要不是证据：结论必须能回到原文 `file:line` 或 `specs/<id>/raw/`；原文与摘要冲突时以原文为准，找不到原文的写「假设」。

## 路由表

| 任务 / 文件 | 加载章节 |
|---|---|
| 新任务，类型或风险不明 | `intake` + `verify` |
| typo、文案、单文件小修 | `verify` |
| bugfix，已有失败测试 | `tdd` + `verify` |
| 新 feature、3+ 文件 | `change` + `verify` |
| 不熟悉模块、跨 2+ 模块 | `context` + `change` + `verify` |
| 重构，行为不变 | `change` + `verify` |
| 改契约、数据、安全、依赖 | `change` + `review` + `verify` |
| 改 `openapi/**`、`migrations/**`、`auth/**` | `review` + `verify` |
| 合并 / 发布前 | `verify` + `review` |

## 状态与交接

- 每个任务写 `specs/<id>/state.json`：目标、风险、当前步骤、已读章节、证据、下一步。
- 开始：`guardrails state init --task <id> --task-file specs/<id>/task.yaml`。
- 原文：`guardrails raw add --task <id> --from <path> --origin "<来源>"`。
- 每步：`guardrails state next --task <id> --next "..." --chapter <id>`。
- 压缩后：`guardrails state handoff --task <id>`，恢复本卡 + 当前章节 + state + raw manifest + trace。
- 一个 plan step 一个会话；超过 5 个函数或压缩前强制交接。

## 验证命令

| 用途 | 命令 |
|---|---|
| 受影响测试 | `<command>` |
| 全量测试 | `<command>` |
| 类型检查 | `<command>` |
| lint | `<command>` |
| 架构规则 | `guardrails sync --check` |
| 契约检查 | `guardrails contract diff --base <snapshot> --current <path>` |
| 原文引用 | `guardrails verify-trace --task <id>` |
