# R636 · 轮志（主线对照轮 · 新窗集 w234..w236）

**日期**: 2026-09-22 · **rc = 1** · **DAG**: `eval/rover/r636/dag-r636.md` · **证据文档**: `docs/evidence/RF0001/R636-mainline-new-windows.md`

## 一句话

同件同题集换新窗集跑 12 跑次：**主判据 Q1 PASS**（D=[4,0,15]，中位 4）∧ Q2 非回归 ∧ **但新增判据 `B_family_block` 判 `pair_read_ok=False`**（`w234/agentP-r3` 整族归零 43/58，被中位 58 掩盖）⇒ **rc=1**；铁律 11 前置器 rc=1 ⇒ 质量/成本标「参考（未可验收）」。

## 本轮做了什么

1. **主线对照**：新窗集 w234..w236（与历史 w184..w233 不相交）；P 产品默认档 ×3/窗 + C1 codex 真值 ×1/窗 = 12 跑次；同一枚 AOT 件 `cefd045e8d1d`（`bin_sha_stable=true`）；零产品源码改动。
2. **判据形态收口（R635 候选②③ 落地）**：新增 `B_family_block` —— 本侧跑次**族级归零**独立分类（FAMILY_BLOCK / PARTIAL_FAMILY / CLEAN）+ 与主判据的**并读纪律**（主判据 PASS ∧ 有整族失败跑次 ⇒ `pair_read_ok=False` ⇒ rc ≥1）；**声明先于跑**（起臂前机检闸断言 B 段在位）。
3. **真机两侧有牙**（合成自检不能替代）：`family_block_census_r636.py` 在**冻结跑次**上取两侧样例（`r635/w232/agentP-r2` → FAMILY_BLOCK ∧ `r635/w231/agentP-r1` → CLEAN）⇒ 两侧均按预期（rc=0）；并给出跨轮 base rate census（47 跑次 / 归零 3 / **0.0638**，近三轮每轮各 1 次）。
4. **文献小步**：arXiv query 3 式（前 2 式被工具面拆散 ⇒ 不计入空采信；第 3 式走 `cat:cs.SE` 最新 feed 有效）+ 摘要 API 1 次 ⇒ **采信 2 条**（L-adopted-8「聚合读数按构造掩盖族级回归」/ L-adopted-9「终态合法 ≠ 过程合规 + 无变异负控则错误提交被放行」）⇒ 台账 690→748 行。
5. **基线台账**：新增 `F_merge.quality.family_block_scan`（pin → `fabd36642cd8`）。

## 读数（详见证据文档）

| 面 | 读数 |
|---|---|
| Q1 主判据 | D=[4,0,15] · 中位 4（阈 −2 / 逐窗 −15）⇒ **PASS** |
| 有效窗 | 3（真值跑通 ∧ 非自败例 ≥1） |
| Q2 次级 | 整题全对 P 7/9 vs C1 1/3 ⇒ 非回归 |
| **B_family_block** | 归零 1（w234/agentP-r3）· 部分 1（w235/agentP-r2）· 干净 7 ⇒ **pair_read_ok=False** |
| 成本（P vs C1，归一后） | 每跑次调用 2.00 vs 7.33 · 新算 1,476.7 vs 5,031.3 · completion 4,352.2 vs 3,221.0 |
| 铁律 11 | **rc=1**（w234/agentP-r3 43/58 · w235/agentP-r2 55/58） |

## 自捕器件缺陷（4 条，判决不翻案）

| # | 缺陷 | 修法 | 留档 |
|---|---|---|---|
| E1 | aux **语料**缺件（只带了脚本）⇒ 前置器全 12 臂 `cases=0/0` **假红** | 冻结源逐字节复制（sha 同值）+ **只重跑后处理、零重测**；`run_r636.sh` aux 机检 1 件→2 件 | `precond-r636-v1missingaux.json` |
| E2 | census 首跑未剔 VOID ⇒ `cli_rc=124` **挂死**被读成 **FAMILY_BLOCK** | 修**输入集**、分类器零改动（判据零放宽） | `family-block-census-r636-v1prevoid.json` |
| E3 | census 首跑早于本轮产物落盘（口径不实） | 重跑 + pin 重钉（`f57549ef5d60`→`fabd36642cd8`），两版并列 | `family-block-census-r636-v2pre636.json` |
| E4 | registry 新行 `covers[]` 的**叙述**条目含**半角斜杠** ⇒ 被 R2c 判为路径且不存在 ⇒ 形式门禁 **13/14** | 文案改全角顿号（阈值/判据零改动）⇒ **14/14** | 与 R635 同类（R2c/R2e）同源 |

## 诚实边界

无单变量轴（不计单变量轮）· n=9/档欠功率 · 跨轮禁相减 · B 分类不重算质量列 · base_rate 只作描述性读数 · 真值自败 w234 4 例 / w236 15 例（照原样判、`policy_demoted` 非本侧臂）· 族级归零只复现**未归因** · 三档终局目标读数不动不宣称。

## 下一步候选

1. **`wythoff` / `sub` 族级归零的只读定因轮**（禁预防性修复）：在冻结产物上逐例定位（构造缺陷 vs 产物缺陷 vs 判据缺陷三类分判），零产品改动。
2. **L-adopted-9 的过程级断言候选**（须放行：动题集/夹具）——末态合法 ∧ 过程违规的样例构造性验证。
3. **最低族栏**（minimum per-family lift）纳入判据列（L-adopted-8 的实施侧）——纯判据面改动，可下轮同窗复算（零重测）。
4. `B_family_block` 的**跨轮 schema 扩展**已在 `honest_bounds` 登记：与 R634/R635 rc 列禁相减。
