# 执行入口

> 本文件不再承载 13KB 流程。流程已经拆成 `manual/00-card.md` + `manual/chapters/*/SKILL.md`。

## 每次任务

1. 读 `manual/00-card.md`（常驻卡，≤80 行）。
2. 跑 `guardrails brief --task specs/<id>`，只加载它选中的 1–3 个章节。
3. 按当前章节执行；不要一次读完 `manual/`。
4. 上下文压缩后，只恢复：常驻卡 + 当前章节 + `specs/<id>/state.json`。

## 章节

| 章节 | 何时加载 |
|---|---|
| `intake` | 新任务，类型或风险不明 |
| `context` | 不熟悉模块、跨 2+ 模块 |
| `change` | 新 feature、3+ 文件、契约/数据变更 |
| `tdd` | 实现或修 bug |
| `verify` | 每次提交/合并前 |
| `review` | 契约/数据/安全/R2+、发布 |

## 为什么不再是一份大手册

- 隐式路由会塌缩：skill 库越大，agent 越可能什么都不加载。
- 所以用显式 `guardrails brief` 预选，而不是让 AI 自己翻目录。
- 章节上限 6 个，每任务上限 3 个；超过就 lint 失败。

## 校验

```bash
guardrails lint-manual
guardrails sync --check
guardrails eval-routing
guardrails doctor
```
