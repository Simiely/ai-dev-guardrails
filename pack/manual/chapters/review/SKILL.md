---
name: review
description: >-
  用于涉及契约、数据、安全或 R2+ 风险的改动，生成后果卡、ADR、回滚和发布方案。
  不要在低风险单模块改动、typo 或纯文档改动中使用。
when_to_use:
  - 改契约、数据模型、安全策略
  - 新增依赖或模块
  - R2+ 或需要发布
when_not_to_use:
  - 低风险单模块改动
  - typo、文案
  - 纯文档
globs:
  - openapi/**
  - migrations/**
  - auth/**
  - package.json
  - pyproject.toml
inputs:
  - specs/<id>/evidence.json
  - specs/<id>/trace.yaml
outputs:
  - specs/<id>/review.md
  - adr/ADR-*.md
checks:
  - guardrails card --task
  - guardrails risk --diff
token_budget: 1200
related:
  - change
  - verify
---
# 评审与后果卡

## 目标

让人只看后果，不看全量 diff；高风险改动必须可回滚。

## 步骤

1. 生成后果卡：任务、风险、触及模块、契约变更、新增依赖、影响面、测试证据、回滚命令。
2. 契约/数据/安全变更附 ADR；ADR 写清背景、选项、决定、后果。
3. 人只回答四个问题：影响面可接受吗？契约变了吗？回滚成立吗？有没有新增依赖？
4. 批准绑定 commit SHA；实现者不能批准自己的 PR。
5. 发布前写灰度、观察指标、回滚触发条件。

## 禁止

- 不得自批 PR。
- 不得在没有回滚方式时合并 R3。
- 不得把「测试通过」当成契约变更的批准。
- 不得隐藏新增依赖或生成物。

## 检查

- `guardrails card --task specs/<id>` 生成后果卡。
- 批准记录含 SHA、批准人、时间。
- R3 有 ADR、灰度、回滚演练。
