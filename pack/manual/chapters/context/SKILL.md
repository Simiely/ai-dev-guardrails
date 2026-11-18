---
name: context
description: >-
  用于在跨模块或不熟悉模块时装配最小上下文，并留下可审计的 manifest。
  不要在单文件小修、已有上下文清单或只读 review 中使用。
when_to_use:
  - 不熟悉当前模块
  - 跨 2+ 模块
  - 需要影响面、契约或受影响测试清单
when_not_to_use:
  - 单文件小修
  - 已有当日 context manifest
  - 只读 review
globs: []
inputs:
  - specs/<id>/task.yaml
  - guardrails.yaml
outputs:
  - specs/<id>/context.md
checks:
  - guardrails brief --task
  - guardrails affected --files
token_budget: 900
related:
  - change
  - verify
---
# 上下文装配

## 目标

只加载任务需要的最小上下文，并留下可审计的 manifest。

## 步骤

1. 从 `guardrails brief` 拿章节清单和 token 预算。
2. 读当前模块 `MODULE.md`、`FLOW.md`；只读直接依赖的 `CONTRACT`，不读实现。
3. 读相关 ADR 和契约快照。
4. 用 `guardrails affected --files ...` 列受影响测试。
5. 写 `context.md`：读取清单、未读清单、假设、待确认、manifest hash。
6. 超过预算时，先删兄弟模块和传递依赖，不删当前模块源码。

## 禁止

- 不得全库 grep 当上下文。
- 不得读兄弟模块实现或传递依赖。
- 不得凭记忆补文件内容。
- 不得在没有 manifest 的情况下开始改代码。

## 检查

- manifest hash 与 `brief` 输出一致。
- 清单里的每个文件都真实存在。
- 待确认问题不超过 3 个，每个附默认建议。
