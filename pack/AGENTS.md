# 项目红线

> 本文件只放「必须遵守」的规则和命令，不超过 200 行。
> 详细流程见 `docs/EXECUTION.md`，本文件不重复解释。

## 开始任务前

- 完整读 `docs/EXECUTION.md` 第 1–5 节。
- 先输出「任务分级 + 上下文清单」，再动手。
- 分级规则见 `docs/EXECUTION.md` 第 3 节。

## 绝对禁止

- 修改 `ARCHITECTURE.md`、`registry.yaml`、`adr/`、CI 配置。
- 删除或跳过测试；修改断言以迁就实现。
- 用 `@ts-ignore`、`eslint-disable`、`noqa`、`allow(...)` 绕过检查。
- 跨模块 import 内部文件（只能 import 对方的 `CONTRACT`）。
- 未经批准新增依赖或新增模块。
- 自己批准自己的 PR。
- 同一问题失败两次后继续重试。

## 约定

- 一次只做 `plan.md` 里的一个步骤。
- 偏离 plan：先更新 `plan.md`，再继续，两者同一次提交。
- 不确定就问，最多 3 个问题，每个附默认建议。
- 顺手发现的问题写进「发现」栏，不顺手改。

## 验证命令

> 把 `<command>` 换成真实命令，并同步到 `ARCHITECTURE.md` 第 7 节。

| 用途 | 命令 |
|---|---|
| 受影响测试 | `<command>` |
| 全量测试 | `<command>` |
| 类型检查 | `<command>` |
| lint | `<command>` |
| 架构检查 | `<command>` |
| 漂移检查 | `<command>` |
