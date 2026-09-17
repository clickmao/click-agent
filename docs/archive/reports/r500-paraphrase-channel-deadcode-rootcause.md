# R500 · 本地改写通道真机 4 臂 —— H1 证伪 + 根因定位（通道被 R444 后置否决吞掉）

状态: 完成（判据 **FALSIFIED**，如实登记，不修判据凑绿）
轮号: R500（承接 R499 预注册 `eval/rover/r499/prereg_r499.json`；本回合新增 `eval/rover/r500/prereg_r500.json`，先于首跑落盘）
被测产物: `/tmp/pub_r499/agenthost`（sha16 `3a79bbb4cfbec807`，IL 警告 0，15,409,088 B）
窗口: 2026-09-17 01:44–02:19 CST（同会话、同二进制、同网格；网格 `task-p17-code.json` 与 r497 **逐字节同**）
臂: C（`AGENTFRAMEWORK_LOCAL_PARAPHRASE=off`）+ P1/P2/P3（`=1`，n=3 重复跑）

## 一、真机读数（同窗单变量）

| 臂 | 改写闸 | 调用数 | 付费 tokens | Δtok vs C | t8 basis | 判据 |
|---|---|---|---|---|---|---|
| C | off | 13 | 71,294 | — | `mechanical:nonack→remote` | **GREEN** red=0 |
| P1 | on | 12 | 78,556 | **+10.19%** | `gate:skip_rejected_nonack→remote` | RED red=1 |
| P2 | on | 12 | 72,222 | **+1.30%** | 同上 | RED red=1 |
| P3 | on | 12 | 70,415 | **−1.23%** | 同上 | RED red=1 |

中位 **+1.30%**（区间 −1.23%..+10.19%）；调用数 13 → 12×3；空正文各 1；teardown **4/4 clean**（procs=None / listeners=[]）；臂 flags 正控通过（C `local_paraphrase=off`、P1/P2/P3 `=on`，其余 `replay_pair_trim/tool_decl_channel/action_boundary/repeat_skip` 全 arm 一致）。

## 二、判据裁决

| 判据 | 内容 | 结果 |
|---|---|---|
| H1 | P 臂 t8 basis 含 `paraphrase`（吸收或降级二载体均可） | **FALSIFIED 3/3** —— 三臂均为 `gate:skip_rejected_nonack→remote` |
| H2 | 改写守卫（非空/非模板/非复读/长度比/无动作宣称） | **不可判**（通道未生效 ⇒ 无改写产物） |
| H3 | C→P 成本降幅 ≥30% | **不成立**：中位 +1.30%，且**不得归因于改写**（通道未生效，差 = 调用数差 + 上游摆动） |
| H4 | C 臂门态正控：t8 不含 paraphrase 且该轮有远端调用 | **PASS**（`mechanical:nonack→remote`，远端调用 1，`paraphrase_degrade_remote` 行 0） |

## 三、根因（机取，非推断）

1. **吸收支确实生效**：P 臂 t8（`换个说法。`，msg_sha16 `eb52df19f61ca2b8`）遥测 `local_turn_gate_reject.kv.r1_raw_len = 21`，**等于字面量 `"mechanical:paraphrase".Length == 21`** ⇒ 该轮 `gateOutcome` 来自 `IndustrialAgentV2.cs:1607-1613` 的**改写吸收支**（`Decide(Skip,"mechanical:paraphrase")`），而不是 r1 判决。⇒ 族匹配器 `LocalParaphraseChannel.ShouldAbsorb` **工作正常**。
2. **吸收立即被否决**：`IndustrialAgentV2.cs:1636-1638` 的 R444 后置否决条件为 `Skip ∧ ¬MechanicalAck ∧ ¬IsPureRepeat` —— 改写族按构造就是「¬Ack ∧ ¬repeat」，而该条款**写在改写族存在之前，未豁免改写族** ⇒ 命中后 `gateOutcome = Pass("gate:skip_rejected_nonack")`（`:1656-1657`）⇒ 走远端。
3. **不变量告警同源**：`:1642-1649` 因 `GatePrefilterOn` 为真而落盘 `gate_prefilter_invariant_violation`（P 臂 1 次/轮，C 臂 **0** 次）—— 这正是「前置门开启时本支不可达」的告警被自己触发。
4. **结论**：R498 实施的本地改写通道在生产形态下是**死代码**（任何吸收必被后置否决吞掉）；C↔P 行为差异仅体现在多一次否决落盘与调用数 −1。该文件 `:1602-1605` 的「位置纪律」注释已预警此类「接线了但没生效」的坑，本次由真机读数复现。

## 四、候选台账（逐项）

| # | 候选 | 状态 | 依据/原因 |
|---|---|---|---|
| ① | 真机 4 臂（C + P×3） | **做** | 4/4 rc=0；`analyze_r499.json` arms=4 missing=0 |
| ② | 判据器 3 态负控 | **部分** | `nc_c_absorb`（R499 干跑）已抓；另两态依赖「通道生效的 P 臂」⇒ 随 H1 证伪**不可判**，登记 not_run |
| ③ | 起手闸连续 2 次 PASS 策略 | **做** | 采样 mem=2801/2792 src_writes=0 ⇒ 2/2 PASS（R499 单采样不可信教训） |
| ④ | 臂执行器实参修正 | **做** | 见「自伤」 |
| ⑤ | 改写族否决豁免（修法） | **结转 R501** | 预注册判据 H1′ |

## 五、自伤（已修，含证据）

`eval/rover/r499/run_rest_r499.sh` P 行传 **5 个实参**（`P 1 r499 49920 49922`），而执行器形参为 `<ARM> [tag] [relay_port] [api_port]` **4 个** ⇒ `relay_real_r475.py:29 PORT=int('r499')` ⇒ `ValueError` ⇒ 首跑 P 臂 0 读数（C 臂已完成，rc=0）。残留（零字节 calls/usage + flags/preflight/prov）归档 `eval/rover/r499/invalid-run2-partial-P1/`；修正版 `eval/rover/r500/run_p_arms_r500.sh`（4 实参 + 闸连续 2 次 PASS + 中止即非零 rc）。C 臂读数**不重跑**（同窗同二进制，01:44–01:57）。

## 六、诚实边界

- 每臂 n=3（P）/ n=1（C）；无置信区间；**跨轮禁相减**（R497/R490 读数不得与本轮相减）。
- 本轮**无任何改写增益**可宣称；H3 的数字仅作通道未生效时的对照读数。
- 改写为**本地 r1 生成**（CPU 成本），不产生付费 token；「省 token」在本形态下只能来自「避免远端调用」，而本轮未出现。
