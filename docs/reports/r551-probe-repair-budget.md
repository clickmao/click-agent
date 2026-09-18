# R551 · 探针证据回灌的**独立预算**（单变量轴 0→1）— 三窗两臂同窗对照

**日期**: 2026-09-18 · **轮号**: R551 · **器具**: `eval/rover/r551/` · **预注册**: `eval/rover/r551/prereg-r551.json`（**先写后跑**）
**状态**: **未达成（铁律 11 前置器 rc=1）** · 机制**已行使**（3/3 治疗窗 `probe_repairs=1`）· 质量**方向为增益**（同窗 w7 56 vs 45，w8 58/58）但**未达验收面 58/58** ⇒ 一切成本/调用降幅标「参考（未可验收）」

---

## 1. 因果链（为什么打这根轴）

- R549 定因：wythoff 族失败机制 = **自建必败点表后未自验落点**；错例含**题面公开用例**而去因是「自测未过仍交付」。
- R550sc 定因（上一 tick）：把既有开关 `AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK` 0→1 后，探针**确实跑了**（`probe=6/8`，公开用例失败被机械抽取），但**那次回灌修复没有发生** —— 唯一的执行回灌预算（`MAX_EXEC_REPAIR=1`）已被 `expect_stdout` 路径用尽 ⇒ **客观证据（题面公开用例回放）无预算可花**，而模型自述路径的预算反而够用。
- ⇒ 本轮单变量 = 把「探针证据驱动的那次回灌修复」**自成预算**：`AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR ∈ {unset(=0, 对照), 1(治疗)}`。轴关时源码条件 `probeRepairs < 0 || execRepairs < MaxExecRepair` 退化为旧条件（**零回归**）。

## 2. 单变量与同输入硬门

| 项 | 值 |
|---|---|
| 变量 | `AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR`：`b0` = 未设(0) / `b1` = 1 |
| 恒开（非变量） | `AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK=1`（两臂同）、`MAX_REPAIR=1`、`MAX_EXEC_REPAIR=1` |
| AOT 二进制 | `/tmp/pub_r551/agenthost` sha256 `e2fdab87b03b3f9ddae1628471b30b6165c07923e5924d77fbf111d24dd5c27b`（15,812,016 B，**IL 警告 0**）；起臂前机检，两臂逐位同 |
| 题面 | sha256 `516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3`（起手硬门断言 ok=True，与 R542/R547/R549/R550 四处既有登记一致） |
| role / 用例 | r542 role · `cases-r521.json` sha256 `270128eb85c7afc0…`（与 r550 副本逐字节同，58 隐藏用例） |
| 窗 | w7/w8/w9，每窗独立 session（`r551-b1` / `r551-b0`），端口 49021/49031 |
| 起手闸 | b1: A1 PASS(2849 MB) · A2 PASS(2854 MB) · B `--leak-selfcheck` rc=0；b0: A1 PASS(2857) · A2 PASS(2863) · B rc=0 |

> 首跑（12:03:01）被起手闸挡下，运行日志原文 `起手闸 A1: GATE_BLOCKED (mem=2707MB)` —— **该 mem 读数高于门限 2650 MB，故成因不在内存**，真因在 build-node 面：本会话自身 `dotnet publish` 遗留的 MSBuild 节点（pid 325890，`/nodeReuse:true`，RSS 241 MB，age 316 s）被闸的 O3「CPU 活跃」判据拒收（该次 gate JSON 已被随后 PASS 记录覆盖，物证 = `logs/run.txt` 首行 + PASS 记录 `build_node_reap.reaped=[{pid:325890, rss_mb:241}]`）。`dotnet build-server shutdown` + 沉降后再采样 CPU 增量=0 ⇒ 重跑过闸（12:03:33）。**归因不写「内存不足」**（R482/R491 假归因条款）。

## 3. 读数（同窗两臂）

| 臂（轴值） | 窗 | 用例 | 调用（transcript / 中继 dump） | prompt tok | completion tok | 探针 | `exec_repairs` | `probe_repairs` | rc / stage |
|---|---|---|---|---|---|---|---|---|---|
| **b1 治疗 (1)** | w7 | 56/58 | 4 / 5 | 33,583 | 8,706 | 7/8 | 1 | **1** | rc=5 `expect_stdout_exhausted` |
| | w8 | **58/58** | 3 / 4 | 24,959 | 7,114 | 8/8 | 0 | **1** | **rc=0 done** |
| | w9 | 43/58 | 3 / 3 | 25,273 | 6,118 | 6/8 | 1 | **1** | rc=5 `expect_stdout_exhausted` |
| **b0 对照 (0)** | w7 | 45/58 | 2 / 2 | 16,852 | 3,459 | 6/8 | 1 | 无字段 | rc=8 `self_test_unmet` |
| | w8 | **VOID** 0/58 | 2 / 4 | 16,539 | 4,042 | – | 0 | 无字段 | rc=4 `contract` |
| | w9 | **VOID** 46/58 | 3 / 5 | 24,915 | 7,042 | – | 1 | 无字段 | rc=4 `contract` |

- **有效窗**: b1 = **3/3**（中位 56，极差 15）；b0 = **1/3**（w7 45/58）。
- b0 的 w8/w9 判 VOID 判据 = 预注册既有规则「`rc=4` 契约面/空产出 ⇒ 对能力命题零信息量」，**保留不删不覆盖**（`readings-r551.json.void`）。
- **上游契约面退化（非本侧代码）**: b0 中继 dump **8 可解析 / 3 不可解析**（`side-agent-004/006/011.json`，`Expecting value: line 1 column 1`）；b1 **12/0**。⇒ 对照臂 2/3 窗死于上游面，**同窗可比样本 n=1**。
- 逐调用恒等式 `prompt = hit + miss`：两臂 **0 违反**（`identity_violations=[]`）。
- 命中率（双口径，`hitrate_dual.py` r551 适配版，窗口↔调用归属取**中继 dump 时间轴**）：b0 `v_all=96.97% / v_incr 95.05–97.79%`（Σ prompt 91,737，Σ miss 2,777）；b1 `v_all=96.11% / v_incr 92.02–95.78%`（Σ prompt 100,423，Σ miss 3,911）。`v_prefix_chars` 分母为**字符** ⇒ 只作口径错示例，不作读数。
- `count_mismatch`：b1 两窗（w7 dump 5 vs 自报 4、w8 4 vs 3）、b0 两窗（w8 4 vs 2、w9 5 vs 3）⇒ **自报低估**，调用数一律以中继 dump 为准（承 R550sc 口径令）。

## 4. 判据逐条（预注册 J1–J5）

| 判据 | 预期 | 实测 | 裁定 |
|---|---|---|---|
| **J1** 机制行使 | 探针有失败证据的窗 `probe_repairs≥1` | b1 **3/3 窗皆 1**（`probe_repair_budget=1`）；同窗探针确有失败（w7 7/8、w9 6/8） | **PASS** |
| **J2** 验收面 58/58 | 3 有效窗全 58/58 ⇒ 前置器 rc=0 | w8 58/58，但 w7 56/58、w9 43/58 | **FAIL** |
| **J3** 调用增幅 ≤ +1/窗 | 治疗臂调用 > 对照臂且 Δ≤1 | 对照臂 w7 以 rc=8 **提前收口**（工作量不等价）、另 2 窗 VOID ⇒ **无等价样本** | **不可判**（不宣称） |
| **J4** 阴性对照 | 轴关 ⇒ transcript 无 `probe_repairs`/`probe_repair_budget` | b0 三窗均**无字段**（与旧台账逐字节同） | **PASS** |
| **J5** 质量不降 | 治疗臂 ≥ 对照臂（同窗两两） | 同窗 w7 **56 > 45**（+11）；b1 中位 56 vs b0 唯一有效窗 45 | **PASS（仅 w7 可比，n=1）** |

**J2 失败的分类（预注册 failure_classification）**：`probe_repairs≥1` **成立**而质量仍不满 ⇒ 属「**修复机会给了但没到位**」，归因在**模型/证据措辞面**，**不在接线/触发面**。

## 5. 铁律 11 机检（独立物化 + 58 用例实跑，非自报）

```
python3 eval/rover/r507pre/exec_precondition.py --round r551     # rc=1
w7  agentR551b0-g1/g1  cases=45/58  rc=1  correct=False  failed=13 例: wythoff#43-public,#44-public,#45,#46,#47,#48,#49,#50,#51,#54,#55,#56,#57 (全 hidden 除外前两条)
w7  agentR551b1-g1/g1  cases=56/58  rc=1  correct=False  failed=2 例: wythoff#43-public, wythoff#57-hidden
w8  agentR551b1-g1/g1  cases=58/58  rc=0  correct=True   failed=[]
w9  agentR551b1-g1/g1  cases=43/58  rc=1  correct=False  failed=15 例: wythoff#43-public,#44-public,#45…#57 (连续)
SELF_REPORT_AGREES=True   ACCEPTABLE_SCOPED=False   VERDICT_BLOCKED ⇒ rc=1
```

- 独立重跑与运行树自报**逐值一致**（`SELF_REPORT_AGREES=True`）。
- 失败**100% 落 `wythoff` 家族**（R549/R550sc 家族归因第 3 次独立复现）。
- **`wythoff#43`（题面公开用例）在 b1 三个窗全部失败** ⇒ 治疗臂的探针确实**看见了**这个错（w7 7/8、w9 6/8）却**仍未修对** ⇒ 与 §4 的分类一致。

## 5b. 残余失败的**文本级定因**（本轮新增，独立重跑 + 语义校验）

对公开用例 `wythoff#43`（stdin `21 25`，期望 `WIN 15 15` —— 语义 = **取子量 (i,j)**，取 15/15 后落 `(6,10)`，而 `(6,10)=(⌊4φ⌋,⌊4φ²⌋)` 是必败点）逐窗**跑最终产物**并按「合法性 + 落点必败性」分类（P 判据用独立算式 `x==⌊(y−x)φ⌋`，非产物自身代码）：

| 臂/窗 | 最终产物实际输出 | 类别 | 物证（源码行） |
|---|---|---|---|
| b1 w8（58/58） | `WIN 15 15` | **OK_WIN** | `is_losing` 用整数 `⌊d·φ⌋==x`（`math.isqrt(5d²)` 校正）⇒ P 判据正确 |
| b1 w7（56/58） | `WIN 1 13` | **illegal_move** | 候选枚举只有 `if i==0 and j==0: continue`，**缺 `i>0 and j>0 and i!=j 排除`** ⇒ 选出「两堆取不等量」的非法着法（其*落点* (20,12) 反倒是必败点） |
| b1 w9（43/58） | **崩溃** `rc=1` | **CRASH** | `wythoff.py:34 return 'WIN '+str(best[0])…` ⇒ `TypeError: 'NoneType' object is not subscriptable`；成因 = 自建判据 `_rook_win` 用**三角数** `d==ia(ia+1)/2 and a==d` 顶替 `a==⌊dφ⌋`，于是 15 例全判 N 位、`best` 恒为 `None` 且**无兜底** |
| b0 w7（45/58） | `WIN 0 14` | **non_winning_move** | 自建 `losing` 集合只枚举 `i,j≥1`（漏整行/整列 `(0,k)`）⇒ 落点 (21,11) 非必败点 |
| b0 w9（VOID） | `WIN 0 12` | **non_winning_move** | 同上 |

⇒ **本轴把失败类别从「打错落点」推向「着法非法 / 崩溃」**：三窗缺陷**互不相同**，且治疗臂的 w9 是**崩溃**而非错答；**探针在这一窗明确看见了 2 条公开用例失败（`probe_failed=2`）且回灌修复确实发生（`probe_repairs=1`），产物仍崩溃** ⇒ 与 §4 的「机会给了但没到位」一致，并给出具体缺口 = **修复后不重跑探针 / 崩溃未被判为不合格（rc=5 仍交付）**，即 R549 定因「自测未过仍交付」在**加了探针预算后依旧存在**。⇒ 下一根轴的靶点应是**交付闸**（探针失败 ⇒ 拒绝交付/降级），而非再加预算。

### 5c. 与外部真值同错（关键对照，实证）

外部真值 codex 臂在 **R531 w2** 上对同一公开用例 #43 的实际输出 = `WIN 1 13`（物证 `eval/rover/r531/run-0917-222519-w2/C-codex/g1/raw/codex-001.jsonl:21`
`aggregated_output":"WIN 1 13\nWIN 0 3"`，与 `10 9 → WIN 0 3` 同批打印）⇒ **与 R551 治疗臂 w7 的输出逐字节相同**。

⇒ 两重含义：① 该错法（两堆取**不等量** = 非法着法）是**模型族共有**，**不是本项目管道特有**（R531 计划文档已记 codex 13/15 含此例）；② 主线「质量不降」的判定若以 `wythoff#43` 这类**外部真值自己也错**的条目为唯一裁判面，会把「同错」读成「我方更差」⇒ 验收面应把**双方共错条目**单列（本轮未改判据，只登记事实；改判据须先写后跑）。

## 6. 同尺 KPI（承 R549 口径）

| 列 | 调用（Σ dump） | Σ prompt tok | 质量（Σ 用例 / 满） | 备注 |
|---|---|---|---|---|
| R1 治疗 b1（R551，本轴=1） | 12 | 100,423 | 157 / 174 | 本轮 3 有效窗 |
| R1 对照 b0（R551，本轴=0） | 11（其中 7 在 VOID 窗） | 91,737（**有效窗仅 16,852**） | 45 / 58 | 仅 1 有效窗 |
| R1 新契约 R548b（**跨轮**，非同窗） | 6 | 50,331 | 163 / 174 | `docs/reports/r549-r548-acceptance.md` §5 |
| codex 外部真值（**跨轮**，非同窗） | 108 | 2,030,796 | 172 / 174 | 同上（9/14/85 调用，2/3 窗满） |

**成本结论（本轮不得宣称降幅）**: 本轴**不降** token/调用，而是**用 token 换质量** —— 唯一同窗可比 w7 上治疗臂 prompt 33,583 / 4 调用（dump 5）vs 对照 16,852 / 2 调用（dump 2），付出 +1~2 次 LLM 请求换来 **+11 例**。⇒ **该轴是质量器械，不是成本器械**；主线「token ↓≥30%」的成立依据仍只在 R1-vs-codex 的跨侧比较（R549: prompt −97.5%、调用 −94.4%），而其**合性**被 `wythoff` 质量面卡住（163 vs 172 / 174）。

## 7. 本轮交付（文件）

- `eval/rover/r551/run_r551.sh` — 驱动器（起手闸 A1/A2/B + 单变量导出 + 摘要含 `probe_repairs`）。
- `eval/rover/r551/prereg-r551.json` — 预注册（含四组判据、验收面 require/nonrequired、失败分类）。
- `eval/rover/r551/ingest_r551.py` + `hitrate_dual.py`（r551 适配版，**唯一差异 = 窗号列参数化** `--wins`，缺省路径与 R550 版逐位同 —— 同输入差分为证）/ `readings-r551.json` / `source-manifest.json` / `dumps-sha256.json`。
- `eval/rover/r551/snapshots/w{7,8,9}/agent{R551b0,R551b1}-g1/g1` — 不可变快照（VOID 窗不入快照、不入 require，但读数可见）。
- `eval/rover/r507pre/precondition-r551.json` — 铁律 11 机检产物（rc=1）。
- `eval/rover/r551/diagnose_wythoff43.py` + `diag-wythoff43.json` — 本轮新增**定因**器具（对快照跑公开用例 #43，按「着法合法性 + 落点必败性」机械分类，P 判据用非同源 Beatty 算式）。
- 产品侧：`src/agent/r1/{R1Options,R1Pipeline,R1RunResult,R1Transcript}.cs`（本 tick **接管**上一 tick 兄弟会话写出的单变量轴实现并收口）+ `src/agent.tests/R1ProbeRepairBudgetTests.cs`（6/6 PASS）。

## 8. 诚实边界

1. **铁律 11 rc=1**（w7/w9 未满）⇒ 本轮**不得**把任何 token/调用降幅计为验收依据。
2. 对照臂 **2/3 窗死于上游契约面退化**（3/11 dump 不可解析，`rc=4`）⇒ 同窗质量 Δ **n=1**，且**不可归因于本轴**；按预注册「不追加、不挑选」未补窗。
3. 治疗臂质量**极差 15**（43–58）⇒ 单窗读数按 R523 判**噪声**，只报方向不报效应量。
4. `wythoff#43`（公开用例）三窗全败 ⇒ 探针「看见」与「修对」之间仍有缺口。本轮**已做错例文本级定因**（§5b，器具 `eval/rover/r551/diagnose_wythoff43.py` + `diag-wythoff43.json`，对**入库快照**可复现）：治疗臂 w7=**非法着法**、w9=**崩溃交付**、w8=正确；对照臂=**打错落点**。⇒ 未测到的部分收窄为：**探针证据消息本身长什么样**（未截取提交给修复调用的 prompt 文本），故「措辞不可操作」vs「模型不采信」仍未分离。
5. 命中率**不作验收依据**：`v_all` 双口径口径名与单位已写进字段名，但与 R550sc/R548 报告值**不可相减**（跨轮/跨窗禁相减）；另 R550 既有 `readings-r550.json` 的命中率行在**当前 /tmp 树**上不可复现（源树 mtime 已变，见 §9 附注）。
6. 未测：外侧 codex 臂同窗 n=1；`MAX_PROBE_REPAIR>1` 剂量面；探针证据的消息措辞变体。
7. 全量测试 **1882/1882 PASS**（`rc=0`，38 s，`--no-build`）；新轴单测 `R1ProbeRepairBudgetTests` **6/6 PASS**；`LlmServiceStatusTests` 单跑 **4/4 PASS**（本轮该测试为并发敏感现存项）。AOT 重发布 IL 警告 **0**（`IL2*`/`IL3*` 计数 0；其余 4 条为 NU1510×2 / CS0169 / CS0649，非 IL 面）。

## 9. 附注：命中率器具回归（同输入差分，非跨轮相减）

`eval/rover/r551/hitrate_dual.py` 由 R550 版逐字复制 + **只加窗号列参数**（`attribute/run` 增 `wins=` 形参 + CLI `--wins`）。回归证明取**同一输入上两版并列**：在 `/tmp/r550` 树上，R550 原版与 r551 适配版给出**逐字段相同**结果（w1 4 调用 0.9709 / w2 4 调用 0.9709 / w3 2 调用 0.9634）⇒ 适配**零行为变更**。同时发现：R550 入库时记录的 `readings-r550.json` 命中率行（2/2/2 调用）在**当前** `/tmp/r550` 树上**不可复现**（该树 transcript/dump mtime 已变）⇒ R550 的命中率行同样**不得作验收依据**，历史读数不回溯改写，只在次轮登记。

## 10. 下轮候选（R552）

1. **交付闸轴（本轮已定因，最高优先）**：`probe_failed>0` ⇒ **拒绝交付 / 降级**（本轮 b1 w9 探针看见 2 条公开用例失败、预算也花了，产物**仍崩溃交付**）⇒ 靶点从「再加预算」转为「停止条件」。仍只翻**已有**开关/既有组件，不新增夹具。
2. **`MAX_PROBE_REPAIR` 剂量面 {0,1,2}** 同窗 n≥3（本轮只测 0/1 且对照臂样本被上游吃掉）。
3. **上游契约面退化的 fail-closed 计数**入起手闸：同窗 dump 不可解析率超阈值即判该窗 VOID（现为事后人工判）——**只改器具**，不动产品。
4. 对照臂补窗以拿到 n≥2 同窗质量 Δ（须**先写后跑**，并登记上游退化率）。
5. 遗留（承 R547/R549）：δ=1 质量损伤成对检验、旧路径列 n≥5、codex token 接 adapter。
