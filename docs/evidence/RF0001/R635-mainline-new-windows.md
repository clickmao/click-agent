# R635 · 主线对照轮（新窗集 w231..w233）—— 证据文档

- **轮次**: R635（2026-09-22）· 前态锚 = R634b（`a436b69a`）
- **被测件**: `~/.agentframework/artifacts/pub_r630/agenthost` sha256 `cefd045e8d1d42588bb7df2d8f7d3d39bd8401385d6aa5a7895dd3b987d7ba19`（19,870,960 B）· `bin_sha_stable=true`
- **外部真值**: codex CLI `61b0194f3bb6534439c8d26a3ed57d0805f84b884588b761795323eeb92fcf70`（8,790 B），同题面 / 同夹具 / 同窗
- **题集**: 冻结件逐字节（文件 sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a` · payload `e7ddce02f75d2e3ea8a72ef06e6cc91d6dd0a141e897542abbce5117ae39b86f`）∧ aux 同批携带（`run_cases_r521.py` sha16 `d9aecf4d397550b8`）
- **窗集**: w231 / w232 / w233（与历史 w184..w230 不相交）
- **臂**: 12 跑次（P 产品默认档 ×3/窗 + C1 codex 真值 ×1/窗）；零产品源码改动 / 零新增夹具 / 零新增开关
- **held-constant 前缀锚**: `a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e`（M1 面 9/9 命中，`missing_runs=[]`）

## 可复现采集命令

```bash
cd /home/agentuser/AgentFramework
bash eval/rover/r635/run_r635.sh
python3 eval/rover/r635/judge_r635.py --D "$HOME/.agentframework/harness/runs/r635" --pd eval/rover/r635
python3 eval/rover/r635/judge_r635.py --D /tmp/none --pd eval/rover/r635 --selftest
python3 eval/rover/r507pre/exec_precondition.py --round r635
python3 eval/capability/decl_sweep.py --check
python3 eval/capability/status_gen.py --check
```

## 判决读数（预注册照原样判，无放宽）

| 面 | 读数 | 判定 |
|---|---|---|
| M1 锚面前提 | 9/9 跑次有提示面且 == 锚；缺项 0 | PASS |
| Q1 主判据（逐窗配对差 D） | **D = [0, 0, 2]**，中位 **0**（阈：中位 ≥ −2 ∧ 逐窗 ≥ −15） | **PASS** |
| W_floor 有效窗 | **3**（真值跑通 ∧ 非自败例 ≥1） | PASS |
| Q2 次级（整题全对率） | P **8/9 = 0.8889** vs C1 **2/3 = 0.6667** | PASS（非回归） |
| 判据器影子自检 | 6 态 `all_ok=true`（含 B2 成对：自败但跑通⇒有效 / 真值挂死⇒仍剔除） | rc=0 |
| **铁律 11 前置器** | **rc=1**（`ACCEPTABLE_SCOPED=False` · `SCOPE_SOURCE=prereg` · `PREREG=True` · `POLICY_ACTIVE=True`） | **BLOCKED** |

- 真值自败例单列：w231 codex **0** / w232 codex **0** / w233 codex **2**（`wythoff#55-hidden`、`wythoff#57-hidden`）⇒ 按 B1 **不构成窗失效**；该真值臂 `policy_demoted`（`unreliable_excluded`）单列 `unreliable_windows=[w233/codex]`。
- 验收面 blocked（1 项）：`w232/agentP-r2/g1` rc=1 · **43/58** · failed = `wythoff#43-public, #44-public, #45..#57-hidden`（**15 例 = 整族**）。
- 成本三列（中继 dump 时间轴）：P n=9 `18 调用 / 16,639 新算 / 44,653 completion`（v_all 中位 0.9039 / v_incr 0.8407）；C1 n=3 `36 / 22,806 / 14,944`（0.9201 / 0.9306）。
  归一列（分母 9 vs 3 的诚实读法）：每跑次调用 **2.00 vs 12.00（−83.3%）** · 每跑次新算 **1,849 vs 7,602（−75.7%）** · 每跑次 completion **4,961 vs 4,981（−0.4%）**。

## 判据与时序前置

- 预注册 `written_before_run=true`（`prereg-r635.json`，sha256 `f1f71df3e079ec951db63e102cb924ae567809f4a4f057570acc555fd8507e45`），含 **`evidence_scope`**（require 12 项显式声明，承 R634 E2 修正）与 **`unreliable_policy`**（B1/B2/B3/B4 机检条款）。
- 起手闸：ceiling 2841MB · prev_swing 75MB · MARGIN 75 · REQ 2725 · A1/A2 PASS · leak-selfcheck rc=0 · 前提闸 PASS。
- 判据器 `judge_r635.py` sha12 `b0934661d0c7`；runner `run_r635.sh` sha12 `204a2b5ac3b6`。
- **收口门禁**：`status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· `decl_sweep --check` `checked=30 drifted=0` · 形式门禁 **14/14**（Failed 0 / Passed 14 / Skipped 0）。
- **自捕 1 条（登记行形态，同轮修，判据零放宽）**：registry 新行首跑形式门禁 **13/14** —— `R2c`（`covers[]` 是**纯路径清单**，我那一条叙述性文案含半角斜杠 ⇒ 被当路径解析 ⇒ 判「路径不存在」）+ `R2e`（`pin_status=live` 的行**不得带 `artifact_sha12`**）。修法 = 文案去斜杠 + `artifact_sha12=null`，改前以「序列化器逐字节复现原文件」断言保形，**未动任何阈值/判据** ⇒ 修后 **14/14**。教训入册：`covers[]` 禁混叙述；live 行 pin 语义 = 不钉字节（字节钉只属冻结件行）。

## 诚实边界

1. **铁律 11 rc=1** ⇒ 本文件全部质量/成本读数**未过可验收前置**，一律标「参考（未可验收）」，**禁**作验收依据、禁对外宣称降幅。
2. **无单变量轴**（预注册自陈）⇒ 测量轮，只作「同件 / 同题集 / 新窗集」并列面，**禁跨轮相减**；R634（D 中位 −3，不达）与本轮（D 中位 0，达）只并列。
3. **主判据 Q1 PASS 不得读作能力达标**：同批 1/9 跑次在 wythoff 族整族失败（15/58）并被铁律 11 拦下；中位口径**看不见**该跑次 ⇒ 中位判据必须与逐臂-题可执行面成对读。
4. n=9（P）/3（C1）**欠功率**；真值侧跨轮成本摆幅（25→36 调用，+44%）**大于**任何臂间差 ⇒ 成本面不作结论。
5. 成本三列总和为**异分母口径**（9 vs 3 跑次）⇒ 归一列与总和列**必须并报**，不得用总和列单读。
6. 真值非硬上限：w233 真值自败 2 例单列；`unreliable_policy` **只对本轮声明之后产生的窗生效（拒绝追溯）** ⇒ R634 及更早判决不翻案、不改写。
7. wythoff 族为 R621/R622 登记的**承重缺口**；本轮**只复现、未做机制归因**（测量轮无产品改动）⇒ 不沿用旧结论定因。
8. 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**（终局目标，非本仓已达标读数）。
