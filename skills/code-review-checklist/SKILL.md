---
name: code-review-checklist
description: 代码审查清单 — 安全/性能/可维护性/测试四维检查
version: 1.0.0
license: MIT
keywords:
  - 代码审查
  - code review
  - 审查清单
regex_patterns:
  - "(审查|review).{0,4}(代码|这份|这个)"
domain_words:
  - review
  - 审查
priority: 5
---

# Code Review Checklist

## 安全 (Security)

- [ ] 输入校验: 外部输入全部经过校验/转义
- [ ] 凭据: 无硬编码密钥/密码, 凭据走环境变量间接
- [ ] 注入: SQL/命令/路径注入面已覆盖

## 性能 (Performance)

- [ ] 热路径无重复计算 (缓存/短路)
- [ ] 集合操作复杂度合理 (无意外 O(n²))
- [ ] 异步路径无同步阻塞 (`.Result`/`.Wait()` 禁用)

## 可维护性 (Maintainability)

- [ ] 命名表意 (无需注释解释命名)
- [ ] 单一职责 (一个方法做一件事)
- [ ] 错误信息可操作 (含上下文与修复方向)

## 测试 (Tests)

- [ ] 新行为有测试覆盖
- [ ] 边界条件覆盖 (空/单元素/极大值)
- [ ] 失败路径覆盖 (异常/超时/取消)
