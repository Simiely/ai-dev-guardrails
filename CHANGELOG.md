# CHANGELOG

## v0.6.4 — 2026-11-19

### 模块与架构

- 新增 `guardrails module new`：从 `project.module_root/_template` 创建模块骨架，跨平台替代 `new-module.ps1` 主路径。
- `project.module_root` 可配，默认 `modules`。
- import-linter 生成配置可直接运行：`lint-imports --config .guardrails/importlinter.toml`，不再要求合并到 `pyproject.toml`。
- CI 模板同步更新 Python 架构检查命令。

### 测试

- 新增 module create 与 CLI 测试；共 106 个测试。

## v0.6.3 — 2026-11-19

### 接入与发布

- `doctor` 校验模块路径、`contract`/`public_path` 文件、模块 layer 引用、`project.python.layer_packages`。
- `pack/ci/gates.yml` 固定到 `v0.6.3` tag，避免 CI 跟随 main 漂移。
- README 增加 English Quick Start；DEVELOPMENT 增加发布清单。
- 版本与 AGENTS 基线同步到 `v0.6.3`。

### 测试

- 新增 doctor 配置校验测试；共 100 个测试。

## v0.6.2 — 2026-11-18

### 架构规则

- `project.python.root_package` / `layer_packages`：import-linter 不再假设 `<name>.<layer>` 包结构。
- `modules[].public_path`：跨模块只允许 import 显式公共入口；未配置时默认 `CONTRACT.*`、`index.*` 或 `public/`。
- 收紧 dependency-cruiser 的 `pathNot`，不再放行任意包含 `CONTRACT` 的路径。
- `render_architecture_readme` 同步说明 `public_path` 和 Python 包映射。

### 测试

- 新增 public_path、Python 包映射、schema 校验测试；共 95 个测试。

## v0.6.1 — 2026-11-18

### 测试托管

- `test-lock` 改为按任务写入 `.guardrails/test-locks/<task>.json`；多任务不再互相覆盖。
- `test-check` 优先读当前任务锁，兼容旧 `.guardrails/test-locks.json`；旧锁属于其他任务时明确提示并忽略。
- hook 检查所有锁定该测试的任务；任一任务未批准就拦截。

### 测试

- 新增多任务锁、旧锁兼容、跨任务 hook 测试；共 91 个测试。

## v0.6.0 — 2026-11-18

### 单份可写

- `guardrails init --mode greenfield|brownfield`：brownfield 只复制契约层和手册，不碰现有代码。
- `guardrails init --dry-run`：只报告会复制/冲突的文件。
- `init` 忽略 `.git`、`.gitignore`、`README.md`；默认不覆盖，冲突列清单。
- `guardrails sync` 只覆盖带 generated 标记的文件；未托管同名文件报冲突，需 `--force`。
- `pack/`、`schema/` 作为包内 `_assets` 打包，wheel 安装后 `init`/schema 校验可用。

### 原文与派生

- `specs/<id>/raw/` 只读原文；`raw/manifest.json` 记录来源、时间、sha256。
- 新增 `guardrails raw add/list`：复制原文到 `raw/` 并写入 manifest。
- `trace.yaml` 支持 `acceptance`（验收标准 → 测试）和 `claims`（结论 → 原文/file:line）。
- 新增 `guardrails verify-trace --task <id>` / `--all`，检查 sha256、commit 和行号。
- `state handoff` 带上 raw manifest 和 trace；`brief` 输出 raw sources。
- 卡片新增红线：摘要不是证据，原文优先。

### 任务与风险

- 新增 `guardrails task new --id ... --title ...`，生成 `task.yaml` + intent/spec/plan。
- 新增 `pack/templates/task.yaml`、`pack/templates/trace.yaml`。
- `new-task.ps1` 现在会生成 `task.yaml`。
- `risk.unknown_default` 可配；brownfield 建议设为 R2。
- `commands.contract` 改为带参数的注释示例，避免 `guardrails run contract` 直接报错。

### 测试

- 新增 init（greenfield/brownfield/dry-run/冲突）、sync 冲突、trace、task new、risk 默认值测试。

## v0.5.0 — 2026-11-18

### 运行证据

- `guardrails metrics record`：记录 task / status / tests / duration / rework。
- `guardrails metrics ingest-junit`：从 JUnit XML 导入测试结果。
- `guardrails metrics report`：通过率、失败率（本地代理）、返工率、平均失败测试数。
- `guardrails report` 合并结构信号与本地运行指标。
- `guardrails canary`：跑 canary 套件，首次建基线，后续对比 exit code/output hash，识别回归。

### 测试

- 61 个测试：metrics、canary、state、report、affected、custody、mutation、quality、card、hook、routing、contract、risk、sync、pack smoke。

## v0.4.0 — 2026-11-18

### 长任务与恢复

- `guardrails state init/show/next/set-active`：每个任务一个 `specs/<id>/state.json`。
- `guardrails state handoff`：输出“常驻卡 + 当前章节 + state”，用于新会话或压缩后恢复。
- Claude Code `SessionStart(compact)` 有 active task 时自动输出 handoff。

### 最小质量报告

- `guardrails report`：统计 tests / files / modules / contract snapshots / locked tests / tasks with state / manual 规模。
- 明确标注：历史 DORA/返工指标需要 CI 数据，当前只给结构信号。

### 测试

- 57 个测试：state、handoff、report、affected、custody、mutation、quality、card、hook、routing、contract、risk、sync、pack smoke。

## v0.3.0 — 2026-11-18

### 质量内核

- `guardrails affected`：TS/Python 源码↔测试图，列出受影响测试。
- `guardrails test-lock` / `test-check` / `test-approve`：red 后锁定测试；改动需批准并重新 lock；holdout 一起锁定。
- `guardrails quality`：Python 圈复杂度、函数长度、跨文件重复块；`--fail-on` 可阻断。
- `guardrails mutation`：把改动文件列表传给项目 mutation 命令，只跑 diff 范围。
- `guardrails card`：生成后果卡（风险、模块、契约、依赖、受影响测试、回滚）。
- Claude Code hook 增加“锁定测试文件”拦截。

### 接入

- `pack/ci/gates.yml` 增加 affected map、quality sensors。
- 手册 verify / tdd 章节引用新命令。
- README、使用指南、框架设计同步更新。

### 测试

- 47 个测试：affected、custody、mutation、quality、card、hook、routing、contract、risk、sync、pack smoke。

## v0.2.0 — 2026-11-18

### 定位

- 从“AI 开发总框架”改为“架构契约层”：模块边界、依赖方向、公共契约、风险分级。
- spec/test 状态机、通用 runtime、代码图明确交给 SpecGuard / AGT / Caper / code graph MCP。

### 新增

- `tools/guardrails/` CLI：`init`、`lint-manual`、`brief`、`eval-routing`、`sync`、`contract`、`risk`、`doctor`、`run`。
- `pack/manual/00-card.md` + 6 个章节：intake / context / change / tdd / verify / review。
- `pack/guardrails.yaml` + `schema/guardrails.schema.json` + `schema/skill.schema.json`。
- `pack/eval/routing/`：9 个 routing 基准案例。
- `pack/ci/gates.yml`：真实 CI 门禁，不再 TODO。
- `tests/`：22 个单元测试 + pack smoke test。
- `LICENSE`（MIT）。

### 变更

- `pack/docs/EXECUTION.md` 从 13KB 流程改为执行入口；流程拆进章节。
- `pack/AGENTS.md`、`.claude/skills`、`.kiro/steering`、`.cursor/rules` 改为由 `guardrails sync` 生成。
- `pack/registry.yaml` 删除；唯一机器源改为 `pack/guardrails.yaml`。
- `pack/templates/spec.md` 增加 8 项完整性清单；`review.md` 增加后果卡。
- `docs/框架设计.md`、`docs/使用指南.md`、`DEVELOPMENT.md`、`README.md` 按新定位重写。

### 为什么

- 隐式 skill 路由在库变大时会塌缩：1,000 个无关 skill 时召回 73.6%→27.4%，零加载 9.3%→51.6%。
- 精选 skill 平均 +16.2pp，但 16/84 个任务会变差；2–3 个模块最优。
- 91.8% 的公开 SKILL.md 至少一个缺陷；弱路由元数据和臃肿正文是主因。
- 所以采用：常驻卡 + 6 章节 + 显式 `brief` + `lint-manual` + `eval-routing`。

## v0.1.0 — 2026-11-18

### 文档基线

- `15ac086`：四件套与 `docs/`、`pack/` 首次落盘。

### 新增

- 初始化仓库：4 文件 + `docs/` + `pack/` + repo-kit 机器层（`knowledge` profile，repo-kit 2.8.0）。
- 迁入双轨框架：上轨宪法、中区制品链、下轨四道门。
- 迁入可复制模板包 `pack/`：6 个产物模板、3 个模块骨架、3 个 PowerShell 脚本、CI 模板。
- 新增 `docs/使用指南.md`、`docs/框架设计.md`。
- 新增 `docs/index.md` 人工导航，接入生成索引、反向链接与踩坑索引。
