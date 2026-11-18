# DEVELOPMENT.md · ai-dev-guardrails

## 项目概览

- 目标读者：使用 AI 编程、希望项目能长期迭代的个人开发者与小团队。
- 解决什么问题：AI 在长期迭代中必然出现的结构侵蚀、架构漂移、重复代码与死代码。
- 不做什么：不做 AI 编码工具本身；不承诺消除 bug；不适用于一次性脚本与探索原型。

## 架构说明

四层，边界清晰：

```text
ai-dev-guardrails/
├── 4 文件层    README / AGENTS / DEVELOPMENT / CHANGELOG
├── docs/       方法论文档（frontmatter + 生成索引 + 新鲜度）
├── pack/       可复制产物（项目模板 / 脚本 / 执行说明）
└── tools/      机器层（repo-kit：schema、检查、生成）
```

职责：

- **4 文件层**：给人看。README 是门面，AGENTS 是 AI 入口，DEVELOPMENT 是架构与问题，CHANGELOG 是版本。
- **docs/**：讲清楚「为什么」和「怎么做」，一个主题一页，互相链接。
- **pack/**：只放会被复制到别的项目里的东西，零个人数据，不参与本仓库 frontmatter 检查。
- **tools/**：只做机器能判定的检查，不做语义判断。

数据流：`docs/` 定义规范 → `pack/` 实现为模板和脚本 → 新项目复制 `pack/` → 项目按执行说明运行。

## 关键问题与方案

### 问题：AGENTS.md 的双重身份冲突

**TL;DR**：仓库自己的 AI 规则和要发给用户的 AGENTS.md 模板不能是同一个文件。

- 问题：模板包需要一个 `AGENTS.md` 给使用者的项目用；本仓库也需要一个 `AGENTS.md` 给维护这个仓库的 AI 用。两者内容与读者都不同。
- 根因：同名文件放在同一层级，复制时会互相覆盖，规范也会混在一起。
- 解决：根目录 `AGENTS.md` 只放本仓库的维护规则；项目模板放到 `pack/AGENTS.md`，文档里说明两者区别。
- 预防：任何「既给自己用又给别人复制」的文件，一律放进 `pack/`。

### 问题：PowerShell 5.1 读取无 BOM 的中文脚本会乱码

**TL;DR**：`.ps1` 里有中文时，必须存成 UTF-8 with BOM，否则 PS 5.1 按 ANSI 解析，直接语法错误。

- 问题：`new-module.ps1` 写入后执行，报 `字符串缺少终止符`，中文全部乱码。
- 根因：Windows PowerShell 5.1 对无 BOM 的脚本按系统 ANSI 代码页读取。
- 解决：所有含中文的 `.ps1` 统一用 `New-Object System.Text.UTF8Encoding($true)` 写回。
- 预防：新增脚本后立刻跑一次；或把脚本输出改成纯 ASCII。

### 问题：repo-kit 安装器在 PS 5.1 下空值判断报错

**TL;DR**：`Test-Path -LiteralPath $null` 会中断安装；已在上游副本中加空值保护。

- 问题：`新建仓库.ps1` 跑到 `update-repo-kit.ps1` 时报 `Cannot bind argument to parameter 'LiteralPath' because it is null`。
- 根因：安装器检查 `AGENTS.md` 时直接对变量做 `Test-Path`，在该调用上下文下变量为空。
- 解决：改为 `[System.IO.Path]::Combine([string]$repo, 'AGENTS.md')`，并加 `-not [string]::IsNullOrEmpty(...)` 保护。
- 预防：升级 repo-kit 后重跑一次安装与 `-Check`，确认补丁未被覆盖。

### 问题：模板包要不要参与文档检查

**TL;DR**：不参与。`pack/` 是产物，不是知识页；强行加 frontmatter 会污染用户复制出去的模板。

- 问题：repo-kit 默认检查 `docs/**`，如果扩大到全仓库，`pack/templates/*.md` 会被要求 frontmatter。
- 根因：内容契约面向知识页，模板是给别的项目用的空壳。
- 解决：`schema/taxonomy.json` 的 `include` 只保留 4 文件与 `docs/**`；`ignore` 显式列出 `pack/**`。
- 预防：新增顶层目录时先决定它属于「文档」还是「产物」，再改 `include` / `ignore`。

## 文档维护流程

1. 改规范 → 只动 `docs/`
2. 改模板或脚本 → 只动 `pack/`，同一次提交更新 `docs/使用指南.md`
3. 发版 → 更新 CHANGELOG 与 AGENTS 基线行
4. 每次提交前跑三条命令（见 `AGENTS.md`）

## 生长式拆分

| 触发 | 拆分 |
|---|---|
| `README.md` > 150 行 | 拆到 `docs/使用指南.md` |
| `AGENTS.md` > 150 词 | 拆到 `rules/` |
| `DEVELOPMENT.md` > 200 行 | 拆到 `docs/架构.md`、`docs/问题记录/` |
| `CHANGELOG.md` | 不拆，按版本分节 |

## 边界

- 机器层验证不了「这句话是不是真的」。
- `pack/` 的产品行为需要在真实项目里验证。
