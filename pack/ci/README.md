# CI 门禁

`gates.yml` 是可直接复制到 `.github/workflows/` 的工作流。它做这些事：

1. `guardrails lint-manual`：章节 frontmatter、描述、预算、重复、条件句。
2. `guardrails sync --check`：生成的 AGENTS/Claude/Kiro/Cursor 视图是否过期。
3. `guardrails affected --diff`：列出受影响测试。
4. `guardrails quality --diff --fail-on`：复杂度、函数长度、重复块。
5. `guardrails run affected|full|typecheck|lint`：跑 `guardrails.yaml` 里配置的真实命令。
6. 可选：`guardrails contract diff` 阻断破坏性契约变更。
7. 可选：`guardrails metrics ingest-junit` 导入测试结果；`guardrails canary` 对比基线。

## 配置

把 `gates.yml` 复制到 `.github/workflows/gates.yml`，然后在 `guardrails.yaml` 填：

```yaml
commands:
  affected: "npm test -- --changed"
  full: "npm test"
  typecheck: "npm run typecheck"
  lint: "npm run lint"
```

`guardrails doctor` 会检查这四个命令是否还是 `TODO`。

## 架构规则

`guardrails sync` 从 `guardrails.yaml` 生成：

- TypeScript：`.guardrails/dependency-cruiser.js`
- Python：`.guardrails/importlinter.toml`
- 说明：`.guardrails/README.md`

不要手写两份规则；改 `guardrails.yaml`，再跑 `guardrails sync`。

启用实际检查：

```bash
# TypeScript
npx depcruise --config .guardrails/dependency-cruiser.js .

# Python：把 .guardrails/importlinter.toml 合并到 pyproject.toml
lint-imports
```

## 契约检查

```bash
guardrails contract snapshot --path openapi/order.yaml --out .guardrails/contracts/order.json
guardrails contract diff --base .guardrails/contracts/order.json --current openapi/order.yaml
```

破坏性变更返回非 0，CI 直接阻断。
