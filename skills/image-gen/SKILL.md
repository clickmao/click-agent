# image-gen — 图像生成 Skill (v0.12.0 计划2 R210 方向)

## 触发
输入含「生成图像/画一个/渲染/生成 icon/生成示意图」或任务目标要求产出图形资产。

## 流程 (纯文本收敛环, 零 API 生图)
1. **prompt 优化**: 5.3-flash 将用户需求转为结构化绘图 DSL (JSON shapes[], 词表: rect/circle/line/text, 附色板)。
2. **本地渲染**: LocalSvgRenderer.Render(shapes, w, h, data/generated/{id}.svg) — 纯 SVG 文本落盘。
3. **校验** (收敛环核心): 5.3-flash 读 SVG 源码 (文本!) + 用户需求清单 → 逐项 PASS/FAIL。
4. **收敛**: 全 PASS → 交付 .svg; FAIL → 失败项反馈重生成 (≤3 轮)。
5. **打点**: render_call (renderer 已 emit) + image_gen_round (round, pass_ratio)。

## DSL 词表 (v0)
rect(x,y,w,h,fill) / circle(cx,cy,r,fill) / line(x1,y1,x2,y2,stroke) / text(x,y,content,fill,fontsize)
色板: Catppuccin Mocha 基色 (示例 #1e1e2e/#f38ba8/#a6e3a1/#89b4fa/#cdd6f4)

## 输出
- data/generated/{id}.svg (主产物)
- 校验报告 (per-item PASS/FAIL) 进回复

## 排除
- 不调外部生图 API (用户钦定 R210)
- PNG 转换不在本期 (SVG 直开)
