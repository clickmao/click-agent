# R636 · 主线对照轮（新窗集 w234..w236）—— 证据文档

- **轮次**: R636（2026-09-22）· 前态锚 = R635
- **被测件**: `~/.agentframework/artifacts/pub_r630/agenthost` sha256 `cefd045e8d1d42588bb7df2d8f7d3d39bd8401385d6aa5a7895dd3b987d7ba19`（19,870,960 B，**与 R634/R635 同一枚**）· `bin_sha_stable=true`
- **外部真值**: codex CLI（同题面 / 同夹具 / 同窗）
- **题集**: 冻结件逐字节（文件 sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a` · payload `e7ddce02f75d2e3ea8a72ef06e6cc91d6dd0a141e897542abbce5117ae39b86f`）∧ aux **两件**同批携带（`run_cases_r521.py` sha16 `d9aecf4d397550b8` + `cases-r521.json` sha256 `270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7`）
- **窗集**: w234 / w235 / w236（与历史 w184..w233 不相交）
- **臂**: 12 跑次（P 产品默认档 ×3/窗 + C1 codex 真值 ×1/窗）；零产品源码改动 / 零新增夹具 / 零新增开关 / 零远端新增形态
- **held-constant 前缀锚**: `a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e`（M1 面 9/9 命中，`missing_runs=[]`）
- **本轮器件面新判据**: `B_family_block`（**声明先于跑**：`prereg-r636.json` `B_family_block` 段 ∧ 起臂前机检闸断言，rc=0 才起臂）

## 可复现采集命令

```bash
cd /home/agentuser/AgentFramework
bash eval/rover/r636/run_r636.sh
python3 eval/rover/r636/judge_r636.py --D "$HOME/.agentframework/harness/runs/r636" --pd eval/rover/r636
python3 eval/rover/r636/judge_r636.py --D /tmp/none --pd eval/rover/r636 --selftest
python3 eval/rover/r636/family_block_census_r636.py
python3 eval/rover/r507pre/exec_precondition.py --round r636
python3 eval/capability/decl_sweep.py --check
python3 eval/capability/status_gen.py --check
```

## 判决读数（预注册照原样判，无放宽）

| 面 | 读数 | 判定 |
|---|---|---|
| M1 锚面前提 | 9/9 跑次有提示面且 == 锚；缺项 0；题集双钉逐位同 | PASS |
| Q1 主判据（逐窗配对差 D） | **D = [4, 0, 15]**，中位 **4**（阈：中位 ≥ −2 ∧ 逐窗 ≥ −15） | **PASS** |
| W_floor 有效窗 | **3**（真值跑通 ∧ 非自败例 ≥1） | PASS |
| Q2 次级（整题全对率） | P **7/9 = 0.7778** vs C1 **1/3 = 0.3333** | PASS（非回归） |
| **B_family_block（新）** | n=9：**整族归零 1**（`w234/agentP-r3`，wythoff 15/15 全败）· 部分族 1（`w235/agentP-r2`）· 干净 7 | **`pair_read_ok=False`** |
| Y 自证盲区（诊断） | P 1/9（`w234-r3` pub 6/8 ∧ hid 37/50）· C1 0/3 | 信息项 |
| LD 冻结清单（诊断） | `wythoff#43-public` / `wythoff#57-hidden`；P 1 跑次命中（2 例）· C1 2 跑次 | 信息项 |
| 铁律 11 前置器 | **rc=1**（`blocked_scoped` = `w234/agentP-r3` 43/58 · `w235/agentP-r2` 55/58） | 未可验收 |

- **`verdict-r636.json`**: `rc=1` · label = 「主判据 PASS / B 并读未过（本侧整族失败 n=1: w234/agentP-r3）」· `rc_semantics` 分层 0/1/2/3（B 并读未过入 1 档）。
- **代价列**（中继 dump 时间轴，跨轮禁相减）：P n=9 `18 调用 / 13,290 新算 / 39,170 completion`（v_all 中位 ≈0.9091 / v_incr 中位 ≈0.8496）vs C1 n=3 `22 / 15,094 / 9,663`（0.9249 / 0.9452）。**跑次数不等（9 vs 3）⇒ 总和列异分母**，归一列另报：每跑次调用 **2.00 vs 7.33** · 每跑次新算 **1,476.7 vs 5,031.3** · 每跑次 completion **4,352.2 vs 3,221.0**。
- **VOID 单列**: 本轮 0 条（`void_single_listed=[]`）。

## 本轮核心方法学产出（B_family_block 的真阳性）

R635 发现「主判据（逐窗**用例通过中位**）看不见族级失败」——本轮把该教训**机制化**为独立判据并**声明先于跑**，且它在**新窗集里立刻再次命中**：

- `w234/agentP-r3` = **43/58**，`wythoff` 整族 15/15 全败 ⇒ 分类 `FAMILY_BLOCK`；
- 而**逐窗中位**（w234 = 58）与**主判据 Q1** 均读 **PASS** ⇒ 若无 B 并读纪律，本轮会被读成「达标」；
- `pair_read_ok=False` ⇒ `rc` 抬至 1 ⇒ **中位 PASS 不得单独读作达标**（R635 候选③ 落地）。

跨轮 base rate census（`family_block_census_r636.py`，只读冻结跑次、判据器同源）：

| 轮 | 本侧跑次 | 整族归零 | 部分族 | 干净 | 归零族 |
|---|---|---|---|---|---|
| r631 | 12 | 0 | 6 | 6 | — |
| r633 | 8 | 0 | 2 | 6 | — |
| r634 | 9 | **1** | 5 | 3 | `sub` |
| r635 | 9 | **1** | 0 | 8 | `wythoff` |
| r636 | 9 | **1** | 1 | 7 | `wythoff` |
| 合计 | **47** | **3** | 14 | 30 | base rate **0.0638** |

⇒ 现象在**近三轮每轮各 1 次**（≈11%/轮）**复现于不同窗集与两个族**（`sub` / `wythoff`）⇒ 非偶发。

## 自捕器件缺陷（4 条；判决不翻案）

1. **E1 · aux 语料缺件 ⇒ 前置器全臂假红（真机首次暴露，同轮修）**：`run_cases_r521.py:19-20` 按 `os.path.dirname(__file__)` 解析语料 `cases-r521.json`；而 `eval/rover/r636/cases/` 首版**只携带了脚本、未携带语料** ⇒ 脚本在 `open()` 抛 `FileNotFoundError` ⇒ **rc=1 且零 `CASE` 行** ⇒ 前置器把全 12 臂读成 `cases=0/0` 的 **假红**（首跑 `precond rc=1`）。
   **修法**（承 R633 既定理赔法）：从冻结源**逐字节复制**语料（sha 比对同值）+ **只重跑后处理、零重测** ⇒ `SELF_REPORT_AGREES=True` 且 `cases=43/58 / 55/58` 等真读数出现。首跑读数留档 `$HOME/.agentframework/harness/runs/r636/precond-r636-v1missingaux.json`（**不撤不翻案**）。
   器具补强：`run_r636.sh` 的 aux 机检从 1 件扩到 **2 件**（脚本 + 语料各带 sha 断言，缺件自愈复制，漂移即 `exit 3`）。
2. **E2 · census 首跑未剔 VOID 跑次（器具层，同轮修）**：首版输入集把**同质超时**跑次（`r633:w227/agentP-r2`，`cli_rc=124` 整轮挂死）读成 `FAMILY_BLOCK` ⇒ 「挂死」与「整族归零」被混成一类。**修法 = 修输入集、不改分类器**（判据零放宽）：VOID 跑次先剔除并**单列**；首跑留档 `family-block-census-r636-v1prevoid.json`。
   同源纪律：census 分类**直接 import 判据器本体** `family_block_core`（禁第二实现）。
4. **E4 · registry 形态自伤（形式门禁 13/14，同轮修）**：新行 `covers[]` 的一条**叙述**条目含**半角斜杠**（`FAMILY_BLOCK / PARTIAL_FAMILY / CLEAN`）⇒ 被 R2c 当路径判「不存在」⇒ 形式门禁 **13/14**。修法 = 文案改全角顿号（**阈值/判据零改动**）⇒ **14/14**；与 R635 的自捕（R2c/R2e）同源 ⇒ 该类「叙述条目禁半角斜杠」已在两轮各自命中一次。
3. **E3 · census 首跑早于本轮产物落盘**：首跑 `rounds_scanned` 含 `r636` 而该轮当时 0 跑次在盘 ⇒ 口径不实。重跑后 pin 由 `f57549ef5d60` → `fabd36642cd8`，两版读数**并列**（`family-block-census-r636-v2pre636.json` 留档），基线台账条目重钉。

## 判据与时序前置

- **先写后跑闸**（起臂前机检，rc=0 才起臂）：`arms/windows/criterion/scope_require=12/unreliable_policy` 全断言 ∧ **`B_family_block.declared_before_run is True`** ∧ bars B1–B4 在位（缺 B 段 ⇒ fail-closed 不起臂）。
- **影子自检**（`--selftest`）：6 态（EQUAL / WORSE_BY_3 / MISSING_TRUTH / TRUTH_SELF_FAIL / TRUTH_VOID / ANCHOR）**+ R636 新增** FAMILY_BLOCK / SYNTHETIC 与 PAIR_READ 两侧有牙。
- **真机两侧有牙**（合成件不能替代，承纪律「只跑一侧 = 未证有牙」）：`family_block_census_r636.py` 取冻结跑次 `r635/w232/agentP-r2` 必判 `FAMILY_BLOCK` ∧ `r635/w231/agentP-r1` 必判 `CLEAN` ⇒ **两侧均按预期**（rc=0）。
- **窗有效性修正**（承 R633 构造缺陷）：有效性 = 「真值跑通 ∧ 非自败例 ≥1」，自败**例**逐条单列（w234 4 / w235 0 / w236 15）；真值挂死/VOID 窗仍剔除（影子自检 `TRUTH_VOID` 有牙证明**未放宽另一侧**）。R633 的 `NO_RESOLUTION` 与 rc=3 **不翻案**。

## 诚实边界

- **无单变量轴** ⇒ 本轮不计为单变量轮（同 R589/R628 先例）；读数只作「同件同题集、新窗集」并列面，**跨轮禁相减**。
- **n=9/档**（3 窗 × 3 跑次）⇒ 欠功率；单窗集不作能力结论；同臂跨窗摆动（历史实测极差 14–15 例）> 任何臂间效应。
- **B 分类是并列读数**：不重算 `cases_pass`、不进中位分母、不改写任何质量列 ⇒ 与 R634/R635 的 rc 列**禁相减**（schema 已扩）。
- **`base_rate` 只作描述性读数**（分母 = 在盘冻结跑次，非全史）⇒ 不作阈值、不进 rc。
- **真值自败**：w234 4 例 / w236 15 例（w236 = 整族）⇒ 两窗对照列标 `unreliable` 并 `policy_demoted`（非本侧臂，`blocked_scoped` 与 `unreliable` 名单**互不重叠**）。
- **铁律 11 rc=1** ⇒ 质量/成本一律标「参考（未可验收）」。
- **三档终局目标读数**（32 ms 级 / 快 50× / −95% · 成本 −85~91%）**不动不宣称**（外部出处，非本仓结论）。
- **census 族级归零只复现未归因**（`sub` / `wythoff` 两族）；机理归因须另开只读定因轮（承 R621/R622 先例）。

## 引用与指针

- 预注册：`eval/rover/r636/prereg-r636.json`（sha256 `3ac2f1b27aa7…`）
- 判决件：`eval/rover/r636/verdict-r636.json` · KPI 表：`eval/rover/r636/kpi-table-r636.json` · 轮志：`eval/rover/r636/report-r636.md`
- 判据器：`eval/rover/r636/judge_r636.py`（sha12 `6ded02c4cf0c`）· 驱动：`run_r636.sh`（sha12 `9d2692429c32`）
- 量表：`eval/rover/r636/family_block_census_r636.py`（sha12 `2759e8dd98e4`）· 结果 `family-block-census-r636.json`（sha12 `fabd36642cd8`）
- 证据级别：**L3**（真机运行：真二进制 + 真依赖 + 真外部真值；一条命令可重跑取同结论）
- kpi 行：`eval/capability/kpi.jsonl` 行 `R636`（带 `baselines` 10 id，RF0004 §4.1 引用义务）
