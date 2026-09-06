---
name: git-commit-helper
description: Git 提交信息撰写辅助 — 按约定式提交规范 (Conventional Commits) 生成/审查 commit message
version: 1.0.0
license: MIT
keywords:
  - 提交信息
  - commit message
  - git commit
regex_patterns:
  - "(写|生成|帮我写).{0,6}(提交|commit)"
  - "commit (message|信息)"
domain_words:
  - git
  - 提交
priority: 6
---

# Git Commit Helper

按 **约定式提交 (Conventional Commits)** 规范撰写与审查 git 提交信息。

## 格式规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

## type 枚举

| type | 用途 |
|---|---|
| feat | 新功能 |
| fix | 缺陷修复 |
| docs | 文档 |
| style | 格式 (不影响逻辑) |
| refactor | 重构 (非新增非修复) |
| perf | 性能 |
| test | 测试 |
| chore | 构建/工具链 |

## 撰写规则

1. subject ≤ 50 字符, 祈使句, 不加句号
2. body 解释 what/why (不解释 how — diff 自己会说)
3. 破坏性变更 footer 标 `BREAKING CHANGE:`
4. 关联 issue footer 标 `Closes #123`
