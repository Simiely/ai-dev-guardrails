# ai-dev-guardrails

> 一套让 AI 在边界内自由发挥、程序长期稳定的开发框架与可复制模板包。

## 这是什么

AI 编程的问题不是单次写不对，而是**长期迭代必然退化**：结构侵蚀、架构漂移、重复代码、死代码堆积。

这个仓库给出一个结构性解法：

- **上轨**：架构宪法（`ARCHITECTURE.md`），人定，AI 不得自改
- **中区**：制品链 `intent → spec → plan → code + tests`，AI 自由发挥
- **下轨**：机器门禁（测试、类型、lint、依赖方向、spec 漂移），判定是否算做对了

## 30 秒理解

| 你遇到的问题 | 对应机制 |
|---|---|
| 越改越漂 | 架构宪法 + spec/code 同提交 + 漂移门禁 |
| 主逻辑不清晰 | `FLOW.md` 强制写主流程、分支表、失败路径 |
| 没有模块化 | `registry.yaml` + 只允许 import 契约 |
| 稳定性差 | 失败测试先行 + 受影响测试 + 四道门 |
| 死代码多 | 三证删除规则：静态无引用 + 运行时无注册 + 测试不依赖 |

## 快速开始

### 1. 复制模板包

把 `pack/` 里的内容复制到你的项目根目录。已有 `README.md` 就不要覆盖。

### 2. 填三个地方

1. `ARCHITECTURE.md` 第 2 节：模块清单和依赖方向
2. `ARCHITECTURE.md` 第 7 节：真实验证命令
3. `registry.yaml`：模块登记

### 3. 建第一个模块和任务

```powershell
.\scripts\new-module.ps1 -Name order
.\scripts\new-task.ps1 -Id order-cancel -Title "订单取消" -Tier T2
```

### 4. 让 AI 开工

```text
读 docs/EXECUTION.md，之后所有任务按它执行。
动手前先输出任务分级和上下文清单。
```

## 仓库结构

```text
ai-dev-guardrails/
├── README.md            门面
├── AGENTS.md            AI / 维护者入口（生成）
├── DEVELOPMENT.md       本仓库的架构与关键问题
├── CHANGELOG.md         版本历史
├── docs/                方法论文档（frontmatter + 生成索引 + 新鲜度）
├── pack/                可复制的模板包（不参与本仓库文档检查）
├── schema/              内容契约与词表
└── tools/repo-kit/      机器层：检查与生成
```

## 文档

- [使用指南](docs/使用指南.md) — 从安装到第一个任务的完整走查
- [框架设计](docs/框架设计.md) — 为什么这样分层，以及证据边界
- [执行说明](pack/docs/EXECUTION.md) — 给 AI 的操作手册
- [开发说明](DEVELOPMENT.md) — 本仓库的架构与关键问题
- [变更记录](CHANGELOG.md)

## 验证

```bash
python -m pip install -r requirements.txt
python tools/repo-kit/check_repo.py --root .
python tools/repo-kit/generate.py --root . --check
pwsh tools/update-repo-kit.ps1 -Check
```

四条全绿才算整理完。

## 边界

- 不适合一次性脚本、纯探索原型、需求还不存在的阶段。
- 机器层只保结构、链接、真源与新鲜度；内容对不对靠人审。
- `pack/` 是产物目录，不参与本仓库的 frontmatter 检查；它的正确性靠真实项目使用验证。
- 框架不能保证不出 bug，只能让错误在合并前暴露、在架构上留痕。
