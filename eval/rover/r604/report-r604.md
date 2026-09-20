# R604 轮志（只读/器具轮 · 2026-09-21）

**主线**：随机游戏/数学题/程序题真机开发任务 × 外部真值 codex（同环境·同输入·同模型）对照做质量自检。
**本轮性质**：只读/器具轮 —— **零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关**。
**预注册**：`eval/rover/r604/prereg-r604.json`（**先写后跑**）；**DAG**：`eval/rover/r604/dag-r604.md`。

---

## 1. C1 起手闸余量条款重派生（候选 ⑤）

| 项 | 值 | 来源 |
|---|---|---|
| 源样本 n | 146 | `~/.agentframework/harness/runs/r603/logs/run-samples.jsonl` |
| min / max | 2584 / 2869 MB | 同上 |
| 极差 swing | **285 MB** | 派生 |
| 现态 ceiling | 2577 MB | 起手前 3 采样 min（本会话） |
| cap = CEIL−GATE−60 | **−133**（< floor 60） | 派生 |
| 判决 | **WINDOW_UNOPENABLE（fail-closed，rc=2）** | 非器具缺陷 |
| 判别力成对控制 | anchor=2650：基础门槛 PASS ∧ 条款门槛 GATE_BLOCKED，`stricter=true` | 纯函数（记录态） |
| 本会话工具子进程 | pyright LSP **249 MB**（pid 2081094），**不在闸 blocker 血统内** | `/proc` RSS 采样 |
| 反事实栏（只报不改） | 回收后 ceiling≈2826 ⇒ cap=116 ⇒ **MARGIN=116 / REQ=2766 / openable=True** | 派生 |

**未行使**：本轮零真机臂 ⇒ 条款**未真机行使（未测）**；反事实栏只报不改，清场属**下一轮起手动作**。

---

## 2. C2 J3 成本判据形态收口（候选 ② · v2）

**两路径交叉**：adapter dump 逐跑次重算 **==** `kpi-table-r{600,602,603}.json` 数组（三轮逐位一致）。
**零回归**：v1（`max_calls`）**三轮逐位复现** `kpi.jsonl` 已登记值。

v2（预注册、**无自由参数**）= `Σ调用数 T ≤ Σ调用数 C` ∧ `逐窗 Σ T ≤ Σ C` ∧ `单位调用新算 prompt T ≤ C`。

| 轮 | v1 形态 | v1 判决 | v2 判决 | v2 越线点名 | 单位新算 prompt（T / C） |
|---|---|---|---|---|---|
| r600 | T_max 4 vs C_max 4 | PASS | **FAIL** | `a2@w186` | 734.0 / 197.0 = **3.726×** |
| r602 | T_max 2 vs C_max 3 | PASS | **FAIL** | `a2@w189` | 770.6 / 247.8 = **3.110×** |
| r603 | T_max 4 vs C_max 3 | FAIL | **FAIL** | `a2@w191` | 598.5 / 232.3 = **2.577×** |

池化调用数（T / C）：r600 18/15 · r602 13/18 · r603 16/17（**a1 三轮全过**，与预声明一致）。

- **形态收口不是放宽而是收紧**：v1 在 r600/r602 的「成本 PASS」是**空心通过**（只数调用、不看单次新算 prompt）。
- **b1 对机制结构性不利**：随附产物必然抬高修复轮的新算 prompt ⇒ 「b1 当闸 vs 只作报告列」须**先预注册**再改（列 R605 ③）。
- **控制三件齐**：POS（注入 calls+2）必红并**点名 a1**；NEG 与 base 同；非平凡（三轮读数互异）。
- **R603 已登记 J3 FAIL 不翻案**（两形态并列留档）。

---

## 3. C3 真值掉线面跨轮 census（候选 ③）

**域**：13 轮 × 3 窗 = **39 窗**，统一源 = run root `cases.txt`（口径与 `judge_r603.read_cases` 同源）。
**守恒**：**10614 / 10614**（早轮每窗 3 产品臂、r600+ 每窗 6 产品臂 ⇒ 通过率取**比率**口径方可比）。

| 项 | 读数 |
|---|---|
| 真值失败用例数 | **13 例**（全部 `wythoff` 族） |
| 真值失败窗次 / 窗口数 | **57 / 17** |
| Top1 `wythoff#57-hidden` | 真值失败 **17 窗 / 12 轮**；我方通过率 **0.5833** |
| Top2 `wythoff#43-public` | 真值失败 **13 窗 / 9 轮**；我方通过率 **0.5000** |
| T1「真值侧掉线用例」 | **成立** |
| T2「我方稳定通过」 | **不成立**（两侧五五**摆动带**） |
| T3 低区分度窗（同类占比 ≥50%） | 无 |
| 窗级 S3（全部产品跑次过 ∧ 真值失败） | **4 窗** |

- 判定：**低区分度候选**，**不作我方收益**；R603 登记的「S3 恒为这两条」与 census 一致（Top2 即此二例）。
- **口径禁混算**：窗级 S3（本文）与 `truthdrop_r603` 的**跑次级** S3（r603 15 行）是两个口径，并列留档。
- 控制：POS（注入 ⇒ 计数 +1 且轮面扩大）、NEG（越域 ⇒ 身份闸 rc=2）、非平凡 ✓。

---

## 4. C4 入册 + C5 文献小步 + 遗留

- **C4**：`docs/external-reference-harness.md` **§12.6**（增量 32 行）= 真值自败窗**显式二选一**（剔除配对 ∧ **单列我方读数** ∧ **不记我方缺陷**；有效窗 = 0 ⇒ 判「无分辨率」**禁筛窗**）+ 真值失败面**两级口径** + 低区分度用例写法。
- **C5**：3 检索式（= 上限）⇒ 采信 **2** · 证伪 0 · 顺延 0：`arXiv:2609.20794v1`（欠定问题点估计评测不足 ⇒ 支持本仓**独立 oracle 解集复核**；代码证据 `eval/rover/r592/landing_predicate_r592.py` + R593 分桶 A 0.0717 / B 0.6595 ⇒ **判据僵硬非缺口主因**）· `arXiv:2609.20822v1`（**声明式约束不承重** ⇒ 支持「转可执行前置步骤」；代码证据 `src/agent/r1/R1Pipeline.cs:192` public_probe → `R1RunResult.cs:12` `rc=8` + 铁律 11 前置器）。台账见 `docs/research/lit-review-ledger.md` §7。
- **遗留 V_int 分布扩展**（`landing_predicate_r593 --rounds r602,r603`）：本轮后台起（日志 `vint-r602-r603.log`，**0 字节**）；**壁钟 424s 零输出、`vint-r602-r603.json` 未落盘** ⇒ 按 pid 清场（4 个进程：wrapper/timeout/主进程 + `-m games wythoff` oracle 子进程，`pgrep` 复核为空）⇒ **本轮零读数入库、如实再顺延**（R602/R603 同因，见 R603 轮志 §4），**不静默跳过**。

---

## 5. 诚实边界

1. 零真机臂 ⇒ **不宣称任何降幅/增益**。
2. C1 条款**未行使（未测）**；反事实栏非实测。
3. C2 两形态**并列**、R603 判决**不翻案**；v2 起效须在**新窗集**预注册后跑。
4. C3 我方通过率为**比率口径**（分母 = 该窗产品跑次数）；跑次级 / 窗级 S3 **禁混算**。
5. 铁律 11 前置器本轮**不适用**（零产品改动、零新臂）。
6. 文献小步只提供**机制假设**，不作收益证据。

**artifacts**：`eval/rover/r604/{dag-r604.md,prereg-r604.json,gate_margin_r604.py,gate-margin-r604.json,judge_j3v2_r604.py,j3v2-r604.json,truthcase_census_r604.py,truthcase-census-r604.json,closeout_r604.py,report-r604.md}` · `docs/external-reference-harness.md` §12.6 · `docs/research/lit-review-ledger.md` §7 · `eval/capability/kpi.jsonl`（R604 行）· `docs/reports/iteration-master-plan.md`（R604 块 + R605 候选）。
