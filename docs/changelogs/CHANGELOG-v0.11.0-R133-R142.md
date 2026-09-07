# v0.11.0 R133-R142 新增能力 (完整归档)

> 归档说明: 本文件为 README 能力段的完整历史归档 (README 30 批一滚动, 只保留最新条目)。
> 生成: R152 (批78, 2026-09-07)。数据源: eval/reports/round-log.md + data/logs/eval/rounds/。
> 制度: 用户钦定 2026-09-07 — "每隔30个批次 更新一次readme", 旧能力段按轮段归档至此。

## v0.11.0 R133-R142 新增能力 (5 KPI 全维度可观测)
- **K1 被提问概率链路修复+深化** (缺陣55): UserTendency 聚合断链 (max-merge + max-conf) — 0→1snip; 画像 snip 可执行化 (4→11tok 行为指导, A/B 差分实证)
- **K4 SKILL 盲区补全**: skill_match (top1/precision/runner_up_gap) + skill_trigger (no_hit/degrade_semantic/force) + 双低压制闭环 (批45 实证 4/5 误吸被压制)
- **K3 语义质量 D4**: reply_rel (bge 512dim 余弦, --embed 子命令) + 阈值分层校准 (模板 0.3/LLM 0.5) + quality_suspect 标记
- **负面样本 21%**: N5 幻觉诱饵 C17 (must_not_contain 防编造断言) + N4 格式陷阱 C18, 批50 全量 19/19 (C17 rel=0.82 未编造)
- **防漂移/意图指数入报告**: compression_index (drift_pass_rate/semantic_avg/chars_ratio) + intent_index (ms_avg/dist) — R142 历史缺口回接
- **D2 健康带口径分带**: quick-5 (550-950tok) / full-19 (900-1300tok) 独立健康带, 19 用例口径批53 in-band

