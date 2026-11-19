# AGENTS.md · ai-dev-guardrails 项目规则

> 📌 **文档基线**：2026-11-19 · v0.6.3（原文/派生/生成、brownfield init、verify-trace、按任务测试锁、public_path、doctor 校验）
> **更新文档后请更新此行**（日期 + 版本），并在 CHANGELOG 追加版本

本仓库维护一套 AI 编程约束框架和可复制模板包。回答相关问题前先读这份，再读 [docs/index.md](docs/index.md)。

## 结构

- `docs/` — 方法论文档，带 frontmatter，受 repo-kit 检查
- `pack/` — 可复制产物（模板 / 手册 / 路由基准 / CI），不参与本仓库 frontmatter 检查
- `schema/`、`tools/repo-kit/` — 机器层：内容契约与校验

## 铁律

- 规范只在 `docs/` 定义一次；`pack/` 不复制规范，只放可执行产物。
- 原文只读、派生可写、生成不手改：`specs/**/raw` 与 `guardrails.yaml` 是源，`AGENTS.md`/adapters/规则是生成物。
- 改 `pack/` 的产品行为时，同一次提交更新 `docs/使用指南.md` 与 `CHANGELOG.md`。
- 不写 token、密码、邮箱、本机绝对路径。
- 机器检查必须全绿：`pytest`、`lint-manual`、`sync --check`、`eval-routing`、`repo-kit`。

## 写作约定

- 标题写判断，不写「关于 X」。
- 每条结论给出验证方式；不能验证的写清限制。
- 外部资料给链接并注明版本。
- 新页从 [docs/_template.md](docs/_template.md) 复制，`status: draft` 起步。

## 常用命令

```bash
python -m pytest -q
guardrails --root pack lint-manual
guardrails --root pack sync --check
guardrails --root pack eval-routing
guardrails --root pack verify-trace --all
python tools/repo-kit/check_repo.py --root .
python tools/repo-kit/generate.py --root . --write
pwsh tools/update-repo-kit.ps1 -Check
```

## 当前规模

- 页面：3（critical=2）
- 按 type：explanation=1, how-to=1, reference=1
- 词表版本：2.8.0

## 边界

- 机器层只保结构、链接、生成物与新鲜度；内容对不对靠人审。
- `pack/` 的正确性靠真实项目使用验证，不靠本仓库的 schema 检查。
