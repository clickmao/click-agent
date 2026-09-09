---
name: image-gen
description: 图像生成流程 — 纯文本收敛环 (prompt 优化 → DSL → 本地 SVG 渲染, 零 API 生图)
version: 1.0.0
license: MIT
keywords:
  - 生成图像
  - 画一个
  - 渲染
  - 生成示意图
  - 生成 icon
domain_words:
  - 图像
  - svg
  - 示意图
priority: 4
type: knowledge_hint
---

# image-gen — 图像生成 Skill (v0.12.0 计划2 R210 方向)

## 触发
输入含「生成图像/画一个/渲染/生成 icon/生成示意图」或任务目标要求产出图形资产。

## 流程 (纯文本收敛环, 零 API 生图)
1. **prompt 优化**: 将用户需求转为结构化绘图 DSL (JSON shapes[], 词表: rect/circle/line/text, 附色板)。
2. **本地渲染**: LocalSvgRenderer.Render(shapes, w, h, data/generated/{id}.svg) — 纯本地。
3. **收敛校验**: 渲染产物回读 → 与 DSL 逐元素核对 (数量/位置/颜色) → 不符则修 DSL 重渲 (≤2 轮)。
4. **交付**: SVG 路径 + 元素清单。

## 约束
- 零外部 API (用户钦定 R210: CogViewClient 生成路径弃用)。
- DSL 词表外元素 → 拆解为基础形状组合。
