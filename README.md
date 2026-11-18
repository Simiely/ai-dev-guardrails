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

给 AI 的第一句话：

```text
先读 AGENTS.md。每个任务先跑 guardrails brief --task specs/<id>，
只加载它选中的 1–3 个章节，不要一次读完 manual/。
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `guardrails init --mode greenfield|brownfield` | 复制 `pack/`；brownfield 只复制契约层和手册 |
| `guardrails task new --id <id> --title ...` | 生成 `task.yaml`、intent/spec/plan |
| `guardrails lint-manual` | 校验常驻卡和 6 个章节 |
| `guardrails brief --task specs/<id>` | 选 1–3 个章节，输出 manifest、token 预算和 raw sources |
| `guardrails raw add --task <id> --from <path>` | 把原文复制到 `raw/` 并写入 sha256 manifest |
| `guardrails verify-trace --task <id>` / `--all` | 校验 trace.yaml 的原文引用、sha256 和 commit |
| `guardrails eval-routing` | 测 routing recall / zero-load / over-load |
| `guardrails sync` | 生成 AGENTS / Claude / Kiro / Cursor 视图 + `.guardrails/` 架构规则 |
| `guardrails sync --check` | CI 检查生成视图/规则是否过期 |
| `guardrails sync --force` | 覆盖没有 generated 标记的同名文件 |
| `guardrails affected --diff` | 源码↔测试图，列出受影响测试 |
| `guardrails test-lock --task <id>` | red 后锁定测试文件 |
| `guardrails test-check --task <id>` | 检查测试是否被改动 |
| `guardrails test-approve --task <id> --reason ...` | 批准测试改动，改完重新 lock |
| `guardrails quality --diff --fail-on` | 复杂度、函数长度、重复块 |
| `guardrails mutation --diff` | 只对改动文件跑项目 mutation 命令 |
| `guardrails state init/show/next/handoff` | 任务状态与压缩恢复 |
| `guardrails report` | 结构信号 + 本地运行指标 |
| `guardrails metrics record/ingest-junit/report` | 记录运行结果、导入 JUnit、看通过率/失败率/返工率 |
| `guardrails canary` | 跑 canary 套件，对比基线，识别回归 |
| `guardrails card --task <id>` | 生成后果卡 |
| `guardrails contract snapshot/diff` | 契约快照与破坏性变更检测 |
| `guardrails risk --diff` | R0–R3 风险分级 |
| `guardrails doctor` | 检查配置、手册、视图、命令、CI、hooks |
| `guardrails hook --event pre-tool` | Claude Code hook：拦截保护路径、锁定测试和破坏性命令 |
| `guardrails run <name>` | 跑 `guardrails.yaml` 里的真实命令 |

## 手册模型

```text
manual/
├── 00-card.md                 # 常驻：目标、红线、路由表、状态、命令（≤80 行）
└── chapters/
    ├── intake/SKILL.md        # 分类 / 风险 / 预算
    ├── context/SKILL.md       # 最小上下文 / manifest
    ├── change/SKILL.md        # intent / spec / plan / trace
    ├── tdd/SKILL.md           # 红-绿-重构 / 测试托管
    ├── verify/SKILL.md        # 门禁 / 契约 diff / 风险
    └── review/SKILL.md        # 后果卡 / ADR / 回滚 / 发布
```

规则：

- 章节上限 6 个；每任务加载上限 3 个。
- 每个章节必须有 `description`、`when_to_use`、`when_not_to_use`。
- 每个章节有 token 预算；超预算就拆到 `references/` 或删。
- 常驻卡不放流程，只放红线、路由和命令。

## 任务模型

```text
specs/<id>/
├── raw/              # 原文层：只读，manifest.json 记录 sha256
├── task.yaml         # id / type / goal / files / risk
├── intent.md         # 派生层：AI 可写
├── spec.md           # 派生层：AI 可写
├── plan.md           # 派生层：AI 可写
├── trace.yaml        # acceptance → 测试；claims → 原文
├── state.json        # 当前步骤 / 已读章节 / 下一步
└── evidence.json     # 门禁结果
```

`guardrails state handoff` 会恢复卡 + 当前章节 + state + raw manifest + trace；压缩后按原文回读，不依赖 AI 自己的摘要。

## 仓库结构

```text
ai-dev-guardrails/
├── README.md            门面
├── AGENTS.md            本仓库维护规则
├── DEVELOPMENT.md       本仓库架构与关键问题
├── docs/                方法论文档（frontmatter + 生成索引）
├── pack/                可复制模板包
│   ├── manual/          常驻卡 + 6 个章节（唯一源）
│   ├── guardrails.yaml  架构契约配置
│   ├── templates/       task / intent / spec / plan / trace 模板
│   ├── specs/           任务目录约定（raw / trace / state）
│   ├── eval/routing/    routing 基准
│   └── ci/gates.yml     真实 CI 门禁
├── schema/              内容契约与配置 schema
├── tools/guardrails/    CLI：lint / brief / sync / contract / risk / doctor / trace
└── tools/repo-kit/      文档检查与生成
```

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

设计与证据边界见 [框架设计](docs/框架设计.md)。关键来源：

- [Lost in Implicit Routing](https://arxiv.org/abs/2610.18522)
- [SkillsBench](https://arxiv.org/abs/2602.12670)
- [What Keeps Agent Skills from Being Reusable?](https://arxiv.org/abs/2608.08453)
- [SkillJuror](https://arxiv.org/abs/2606.11543)
- [Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088)
- [TDAD](https://arxiv.org/abs/2603.17973)
- [SpecBench](https://arxiv.org/abs/2605.21384)
