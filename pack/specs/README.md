# specs/

每个任务一个目录：`specs/<id>/`。

## 目录

- `raw/` — 原文层，只读。原始需求、issue、日志、截图、API 响应。
  `raw/manifest.json` 记录来源、抓取时间、sha256。
- `task.yaml` — id / type / goal / files / risk / unfamiliar。
- `intent.md` / `spec.md` / `plan.md` — AI 派生层，可写；关键结论必须引用原文。
- `trace.yaml` — `acceptance` 记录验收标准 → 测试名；`claims` 记录结论 → `raw/` 或 `file:line`。
- `state.json` — 当前步骤、已读章节、证据、下一步。
- `evidence.json` — 门禁结果。

## 规则

- `raw/` 只读，AI 不得修改；`guardrails.yaml` 的 `protected` 已包含 `specs/**/raw/**`。
- 加原文：`guardrails raw add --task <id> --from <path> --origin "<来源>"`，会自动写 sha256。
- 摘要不是证据；原文与摘要冲突时以原文为准；找不到原文的写「假设」。
- 新建任务：`guardrails task new --id <id> --title "..." --type feature --risk R1`，会生成 `task.yaml`、intent/spec/plan、`raw/manifest.json` 和 `trace.yaml` 骨架。
- 校验引用：`guardrails verify-trace --task <id>`；全量校验：`guardrails verify-trace --all`。
- 压缩恢复：`guardrails state handoff --task <id>` 会带上 raw manifest 和 trace 摘要。
