---
name: r415-gate-pin
description: R415 判别力锚 — 知识提示型探针, 用于钉死「前置门入参 = 用户本轮原文」
version: 1.0.0
license: MIT
keywords:
  - 收到
  - 谢谢
priority: 1
type: knowledge_hint
---

# R415 判别力锚（知识提示型探针）

命中本技能 ⇒ SKILL.md body 作为系统侧知识注入, 尾挂在 prompt.UserMessage 之后（`[技能知识参考]` 块）。

SENTINEL_SKILL_7F3A —— 本哨兵只允许出现在**远端主调用**的请求里。
若它出现在**本地判别请求**里, 说明前置门吃到的是 `prompt.UserMessage`（已追加 role/计划/知识块）而不是
`message.Content`（用户本轮原文）⇒ 门会恒 Pass、r1 增益归零（R413 第三个空心根因）。

判据（外部真值, 见 eval/rover/r415/verdict.py）:
  1) 判别请求的文本必须含用户原文, 且**不得**含本哨兵与 `[本轮参考上下文]`;
  2) 远端主调用必须含本哨兵（正控: 证明该块确实存在于 prompt.UserMessage ⇒ 判据有判别力）。
