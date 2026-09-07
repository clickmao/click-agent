# 历史测试维度总账 (R142 建档, 用户钦定"历史数据不可遗忘")

> 来源: 214 个留存轮 JSON (mass_1..mass_99d+) 1051 个 per-case 样本字段普查 (2026-09-07)。
> 制度: 每轮批测必须覆盖此清单中标注【常驻】的维度; 新增维度在此登记; 删除维度需注明原因与日期。

## 常驻维度 (每轮批测自动采集, summarize_points)

| # | 维度 | 字段 | 建档轮 | 服务 KPI | 备注 |
|---|------|------|--------|----------|------|
| 1 | 判定 | pass/notes | R1 | K5 | 断言体系 intent/llm/skill_force/reply_contains/must_not_contain(R138) |
| 2 | token | prompt/completion/total_tokens | R1 | K2 | D2 健康带分带 (R139): quick-5 550-950 / full-19 900-1300 |
| 3 | 耗时 | wall_ms/llm_ms_total/phase_llm_ms/intent_ms | R1/R129 | K2/K5 | D3 phase_timing 链 |
| 4 | 意图 | intent/subtasks/intent_ms + intent_index (轮级 n/ms_avg/dist) | R1/R142 | K1 | R142 起轮级指数入报告 |
| 5 | 上下文压缩防漂移 | compress_n/drift_ok/semantic/chars → 轮级 compression_index (drift_pass_rate/semantic_avg/chars_ratio) | R129 打点/R142 报告 | K3 | semantic_avg 仅 SummarySentences 档 (rel 0.5-0.8) 触发 |
| 6 | 装配 | assembly_ok/snippets/sources_recall/assembly_ms/from_cache | R7 | K1/K3 | 八源召回画像 |
| 7 | prompt 构成 | prompt_total_tokens/history_tokens | R28 | K2 | 上下文占比 |
| 8 | 证据门 | gate_to_ask | R88 | K1 | EvidenceGate 0.60 |
| 9 | 执行环 | loop_success/loop_ms | R1 | K5 | |
| 10 | SKILL | skill_hits/skill_force/skill_match/skill_decisions | R1/R134 | K4 | 立项卡 T5 |

## 条件维度 (特定用例/触发)

| # | 维度 | 字段 | 用例 | 建档轮 | 备注 |
|---|------|------|------|--------|------|
| 11 | 隔离 | isolated/isolated_score | C14/C16 多轮 | R36 | score≥2 隔离判定; **R149 判定空心修复**: C14 expect 绑 isolated_true 真断言 (不再只 llm:true), quick-11 起常态采集 |
| 12 | bge 真链 | bge_provider/bge_ms | 全局 | R116 | bge-local vs hash-fallback |
| 13 | 语义质量 | reply_rel/quality_suspect | LLM 用例 | R136 | 阈值分层: 模板 0.3 / LLM 0.5 |
| 14 | 历史对比 | delta_tokens_vs_hist/delta_wall_vs_hist | 有基准轮 | R132 | D5 |
| 15 | 长会话 | C16 四轮 REPL | C16 | R119 | 隔离/pivot/回锚 |

## 负面样本族 (cases.json, 21%)

C12 空输入 (N1) / C13 敏感命令 (N2) / C17 幻觉诱饵 (N5, must_not_contain) / C18 格式陷阱 (N4)

## 数据蒸发教训 (R142 实证)

compression 打点 2026-09 R129 即落盘, 但 summarize_points 从未消费 → 轮 JSON 无字段 → 报告层不可见 = **打点≠指标**, 必须闭环到 summarize_points + round-log 才算建成。
