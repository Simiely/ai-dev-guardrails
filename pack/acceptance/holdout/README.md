# holdout acceptance

这里放 agent 不可见、只由 CI 跑的验收测试。

规则：

- agent 不得读取或修改本目录。
- `guardrails test-lock` 会把这里的测试一起锁定。
- `guardrails affected` 不会把这里当成普通单测；CI 应单独跑一遍。
- 至少覆盖主流程和一条失败路径。

删除本文件前先放入真实测试。
