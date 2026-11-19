# ai-dev-guardrails

> 一个 agent 原生的**架构契约层**：把模块边界、依赖方向、公共契约和风险分级变成可生成的 lint 配置、显式路由和 CI 门禁。

它不试图做“AI 开发总框架”。它只做现有工具都没做好的那一层：

- **架构契约**：`guardrails.yaml` 是模块、层、依赖、契约、风险的唯一机器源。
- **手册编译器**：`manual/00-card.md` + 6 个章节，生成 AGENTS / Claude / Kiro / Cursor 视图。
- **显式路由**：`guardrails brief` 只选 1–3 个章节，不让 AI 自己翻目录。
- **证据门禁**：契约快照 diff、风险分级、章节 lint、routing eval、doctor。

## 30 秒理解

| 你遇到的问题 | 对应机制 |
|---|---|
| 越改越漂 | `guardrails.yaml` 生成依赖规则；契约快照 diff 阻断破坏性变更 |
| 主逻辑不清晰 | 6 个章节按工作阶段拆分，每任务只加载 2–3 个 |
| 没有模块化 | 模块登记 + 只允许 import `CONTRACT` |
| 上下文太长被压缩 | 常驻卡 ≤80 行；压缩后只恢复卡 + 当前章节 + `state.json` + `raw/` 原文清单 |
| AI 理不清、摘要失真 | `specs/<id>/raw/` 只读原文 + `trace.yaml` 引用 + `guardrails verify-trace` |
| AI 不加载该看的规则 | 显式 `guardrails brief` 预选，不依赖隐式路由 |
| 规则越写越厚 | 章节上限 6 个；`lint-manual` 抓臃肿、弱路由、重复、条件句 |
| 死代码多 | 三证删除规则：静态无引用 + 运行时无注册 + 测试不依赖 |

## 不是什么

- 不是通用 agent runtime：运行时策略交给 Claude Code hooks / Microsoft AGT / Caper。
- 不是 spec 状态机：spec→人批→red→green 交给 SpecGuard 或等价工具。
- 不是通用代码图：检索交给 Serena / CodeGraph 等 MCP。
- 不强制所有任务写全套 SDD：只对 feature、data pipeline、3+ 文件、高代价改动。

## 单份可写

它只保留**一个可写源**，不维护两份会漂移的副本：

```text
原文层   specs/<id>/raw/ + git commit  只读、不可变
派生层   intent/spec/plan/state/trace  AI 可写，但必须引用原文
生成层   AGENTS.md / adapters / 规则    由 sync 单向生成，不手改
```

原文与摘要冲突时以原文为准；找不到原文的写「假设」。这样压缩后即使理不清，也能按 `raw/manifest.json` 和 `trace.yaml` 回到原始数据。

## 快速开始

```bash
# 1. 安装 CLI（本地开发用 -e）
python -m pip install -e /path/to/ai-dev-guardrails

# 2. 新项目：空目录或只有 .git/README
guardrails init --target . --mode greenfield

# 老项目：只复制契约层和手册，不碰现有代码
guardrails init --target . --mode brownfield

# 3. 填 guardrails.yaml：modules / contracts / risk / commands
# 4. 改 manual/00-card.md 和 manual/chapters/*/SKILL.md

# 5. 校验与生成
guardrails lint-manual
guardrails sync
guardrails doctor
```

## Quick start (English)

```bash
python -m pip install -e /path/to/ai-dev-guardrails
guardrails init --target . --mode greenfield   # or: --mode brownfield
guardrails lint-manual
guardrails sync
guardrails doctor
```

For an existing repository use `--mode brownfield`: it copies only the contract layer and manual, and never overwrites existing files by default. The first instruction to the AI is:

```text
Read AGENTS.md. For every task run `guardrails brief --task specs/<id>`.
Load only the selected 1-3 chapters. Do not read the whole manual/.
```

给 AI 的第一句话：

```text
先读 AGENTS.md。每个任务先跑 guardrails brief --task specs/<id>，
只加载它选中的 1–3 个章节，不要一次读完 manual/。
```

## 常用命令

日常回路只有六条：`init` → `brief` →（改代码）→ `lint-manual` → `sync` → `doctor`；要证明结论仍指向原文时加 `verify-trace`。
完整的 26 条命令表（含 `task new`、`module new`、`raw add`、`eval-routing`、`affected`、`test-lock`、`quality`、
`mutation`、`state`、`metrics`、`canary`、`card`、`contract`、`risk`、`hook`、`run` …）在 [使用指南](docs/使用指南.md)
的「10. 命令速查」——那里是唯一权威表，本页不复制。

## 手册与任务模型

- **手册**：`manual/00-card.md`（常驻卡）+ `chapters/*/SKILL.md`（6 个章节）的目录形态与四条硬约束 → [框架设计](docs/框架设计.md) 的「中区：手册编译器 + 显式路由」
- **任务**：`specs/<id>/` 里 raw / task.yaml / intent / spec / plan / trace / state / evidence 各归哪一层 → [框架设计](docs/框架设计.md) 的「原文、派生与生成」
- **仓库结构**：顶层目录逐项说明 → [docs/仓库结构.md](docs/仓库结构.md)

## 验证

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q
guardrails --root pack lint-manual
guardrails --root pack sync --check
guardrails --root pack eval-routing
python tools/repo-kit/check_repo.py --root .
python tools/repo-kit/generate.py --root . --check
pwsh tools/update-repo-kit.ps1 -Check
```

全部通过才算整理完。

## 边界

- 不适合一次性脚本、纯探索原型、需求还不存在的阶段。
- 机器层只保结构、链接、路由、生成物与新鲜度；内容对不对靠人审。
- `pack/` 的正确性靠 smoke test + 真实项目使用验证。
- 框架不能保证不出 bug，只能让错误在合并前暴露、在架构上留痕。

## 证据

设计与证据边界（强对照 / 实践工具 / 弱预印本三档）见 [框架设计](docs/框架设计.md) 的「证据强度」；7 篇 arXiv 原始链接见该页「参考来源」。

## 文档导航

| 文档 | 类型 | 内容 |
|---|---|---|
| [docs/仓库结构.md](docs/仓库结构.md) | reference | 顶层目录逐项说明 |
| [docs/框架设计.md](docs/框架设计.md) | explanation | 三层结构、手册与任务模型、证据强度与边界 |
| [docs/使用指南.md](docs/使用指南.md) | how-to | 从安装到第一个任务，含完整命令速查 |
| [docs/index.md](docs/index.md) | index | 人工导航；生成索引在 `docs/_generated/` |
| [AGENTS.md](AGENTS.md) | — | AI / 维护者入口与写作约定 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | — | 本仓库自身架构与关键问题 |
| [CHANGELOG.md](CHANGELOG.md) | — | 版本变更 |
