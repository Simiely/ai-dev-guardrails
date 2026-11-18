# specs/

每个任务一个目录：`specs/<id>/`。

最少包含：

- `task.yaml`：id / type / files / goal / risk。
- `state.json`：当前步骤、已读章节、证据、下一步。
- `trace.yaml`：验收标准 → 测试名。

按 `guardrails brief --task specs/<id>` 选中的章节生成其余文件。
