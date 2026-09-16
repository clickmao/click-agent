# R482（2026-09-16）真机双臂：R478 修复上真链 + 主 KPI（一轮 token −32.21%）+ 模板兜底的质量代价

**预注册**：`eval/rover/r482/prereg_r482.json`（首跑之前落盘，H1–H6 逐条含 verdict_rule；
本轮两处**实现偏离**已在 `verdict-r482.json.drift_notes`/`checks_posthoc` 留痕并复原为 prereg 原文口径）。

**唯一变量**：门控（`turn_gate` / `repeat_skip`）。同网格 `p12`、同夹具 `skeptic-growth.rbin`、同二进制、
同中继（`relay_real_r475.py` → `api.deepseek.com/v1/chat/completions`，逐调用 usage 落盘）。

| 项 | Arole（门控关，生产等价分母） | R（r1 在管道内） |
|---|---|---|
| 远端调用次数 | **21** | **14** |
| prompt / completion | 68083 / 4551 | 44444 / 4793 |
| total（=prompt+completion） | **72634** | **49237** |
| 12 轮 | ok 12/12，events 37，blocked 0 | ok 12/12，events 37，blocked 0 |

**主 KPI**：`(72634 − 49237) / 72634 = 32.21%`（≥30% ⇒ R413 验收②在**真上游 + 同一轮双臂**内首次达线）。
调用次数 −7（21→14，≥5 ⇒ 验收③ 可测增益成立）。

## 判据（prereg 原文）

| id | 判 | 读数 |
|---|---|---|
| H1 降幅 ≥0.30 | **PASS** | 32.21% |
| H2 A.calls − R.calls ≥5 | **PASS** | Δ7 |
| H3 A.calls < 21（R478 修复省下浪费重试） | **FAIL** | A=21（=R477 同值）⇒ 按 prereg `fail_action`：**记「修复在真链上无可测效果」并单列，不重跑凑数** |
| H4 R.calls ≤ 10（不劣于 R477） | **FAIL** | R=14（跨二进制参考列） |
| H5 恒等式 `hit+miss==prompt` 逐行 | **PASS** | A 21/21、R 14/14 |
| H6 复述轮逐字回放(≥1) ∧ 无旧误诊文案 | **PASS** | 回放例 `t6←t1`(434B)、`t9←t8`(606B)；旧文案「推理过程占满输出预算」出现 0 次 |

`verdict_all_pass=False`（H3/H4 红，按 prereg 不重跑）。

## H3 为什么红：机制在位、收益 headroom 被上游漂移吃掉

- 机制面**可机检在位**：`point='llm_call_empty_body'` 行 Arole 4 行、R 2 行，`retry_skipped=True` **逐行成立**；
  `empty_cause='tool_call'` 与供应商 `finish_reason='tool_calls'` 4/4 一致 ⇒ R478 的「tool_calls 因 Retryable=false ⇒ 不重试」
  确实生效（改前该分支会白跑一次 32k 预算重试）。
- 但**空正文基数**从 R477 的 15 行掉到本轮 4 行（同一 Arole 配置、同一夹具）⇒ 上游行为漂移，
  该修复能省下的调用数几乎被抽空，`A.calls` 因此没有位移。
- 结论收窄：本轮只证「机制在位」，**不证**「调用数收益」。这与 R477 的 `A.calls=21` 同值，不可当作基线恒定。

## 诚实边界：−32.21% 里有 4 轮模板兜底（prereg H6 未覆盖）

- R 臂 `t2–t5` 的用户可见答复**完全相同**（21B 模板 `收到，继续按当前方向推进，本轮不重新规划。`），
  Arole 同轮为 4 条**各自不同**的实质短答（139/62/12/11B）⇒ R 臂 **实质答复轮 6 < Arole 12**。
  更严的质量变体判据（非 prereg 原文）因此判红，已单列于 `checks_posthoc.quality_verdict_H6c_strict_variant`。
- 即：主 KPI 达线，但其中一部分**不是「本地 r1 生成替代远端」**，而是「管道用固定模板替代了远端」。
  这与 prereg `honest_boundaries_pre` 里那条（本地 r1 只覆盖门控/判定与本地回放，未覆盖本地生成替代）完全吻合，
  是 **R483 的第一顺位**：把模板兜底换成 r1 本地生成，再重测同网格 KPI 与质量。
- 单夹具单次 ⇒ 点估计无置信区间；上游真供应商可漂移；跨二进制（R477 `db187e0eae7f26ea` vs 本轮 `6a9b7aed22a22f48`）只作参考列。
- **本轮无 C# 改动** ⇒ 不重发布 AOT，不冒充新 AOT 证据（`binary_match=true`：实发 sha16 = prereg pin）。

## 起手闸踩坑（可复用）：占用不只有 llama-server

`run_both_r482.sh` 的 R 臂起手闸实测 `MemAvailable=2590MB < 2650MB` 被闸下（Arole 的 llama-server RSS 未释放，同 R477）。
补 `eval/rover/r482/run_arm_R_only_r482.sh` 做沉降等待后**仍红**（2556–2608MB，且 `pgrep llama-server` 已 0）⇒
真因是**本方 `dotnet test` 遗留的 Roslyn 编译服务器 `VBCSCompiler`（RSS 206MB）**。
`dotnet build-server shutdown` 后 `MemAvailable=2730MB` ⇒ R 臂通过并跑完（EXIT=0）。
**修正 R477 的归因**：起手闸前除等 llama-server 释放，还须关本方编译服务器（`$HOME/.dotnet/dotnet build-server shutdown`）。

**器具**：`eval/rover/r482/{prereg_r482.json,run_both_r482.sh,run_arm_R_only_r482.sh,check_r482.py,verdict-r482.json}`；
判据器失败即抛 MISS（源码常量派生，取不到不兜底）。
