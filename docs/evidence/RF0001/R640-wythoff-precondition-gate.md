# R640 · 承重缺口族（`wythoff`）只读逐例定因 ＋ 缺口族**可执行前置步骤**落地 —— 证据文档

- **轮次**: R640（2026-09-22）· 前态锚 = R639（主线对照轮 / 新窗集 w237..w239）
- **轮形**: **零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具语义** —— 只读复算 + 器具面收口
- **被测件**: 无（未重新构建、未重新发布；不含任何新二进制）
- **冻结面**: `eval/rover/r639/snapshots/<win>/<arm>/g1`（w237/w238/w239 × {agentP-r1..r3, codex} = **12 跑次**，只读副本上执行、零写入原树）
- **题集**: `eval/rover/r640/cases/cases-r521.json`（与 r610/r639 **逐字节一致**，`cmp` + sha256 已核）· aux 两件同批携带（`run_cases_r521.py`）
- **真值参照**: `eval/rover/r622/wythoff_oracle.py`（独立实现，与判定器/生成器零共享代码）
- **预注册**: `eval/rover/r640/prereg-r640.json`（`written_before_run: true`）· sha256 `3f2b416f889568b358e90e108cf0402efa4718749d970fa7f116c8d8a62da019`
- **判决件**: `eval/rover/r640/verdict-r640.json`（`rc=2`，分层见下）· 器具自检 `selftest-r640.json`（6/6 PASS）

## 可复现采集命令

```bash
cd /home/agentuser/AgentFramework
# ① 逐例定因（J0–J5b / J9；冻结快照副本上执行，零写入）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r640/attrib_r640.py --det
# ② 缺口族可执行前置步骤（两侧齿证 + 合成四臂）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r640/wythoff_precheck_r640.py --selfcheck
# ③ posthoc 常设件（codex「stdout 优先」重判，任意冻结面）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r640/posthoc_r640.py --face r639
# ④ 判决件（先跑影子自检，再出判决）
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r640/judge_r640.py --selftest && \
PYTHONDONTWRITEBYTECODE=1 python3 eval/rover/r640/judge_r640.py
```

## 判决读数（预注册照原样判，无放宽）

| 判据 | 读数 | 判定 |
|---|---|---|
| J0 oracle 正控 / 变异负控 | 正控 **15/15** ∧ 变异 **10/15 判红**（有牙） | PASS |
| J1 重放 ↔ R639 冻结判决件交叉校验 | 12 跑次逐跑次一致，`mismatch = 0` | PASS |
| J2 守恒式 | `Σ分类 = 12 × 58 = 696`（逐跑次 58）**恰好一次** | PASS |
| J3 机制探针（R637 判别式跨窗迁移） | 真阳性 **1** / 假阳 **0** ⇒ 迁移成立 | PASS |
| J4 逐跑次**行级**最小修复实验 | **1/5 定因**（`w237/agentP-r2 → C1_pm1_window`）；4 跑次**未测到** | 未达标（能力层，记「未测到」非「无缺陷」） |
| J5 三态定因 | 产物侧缺陷 **1** · 未定因 **4** · 夹具缺陷 **0**（J0 排他） | 部分 |
| J5b 变异负控三件 | 同字节重写 ⇒ `0/15`（非「凡改即绿」）· 独立实现 ⇒ `15/15` · 恒 LOSE ⇒ 大量判红 | PASS |
| **J6 可执行前置步骤（v1 预注册器具）** | **两侧齿证双红** ⇒ 器具缺陷 | **FAIL（rc=2，照原样判）** |
| J6v2 修正器具（`checks_posthoc`，下轮重注册） | 四腿全绿（见下） | PASS（事后） |
| J7 `F_lift_min` 分辨力未行使条款 | 最差式 **−12** / 中位式 **−9** ⇒ 同向 ⇒ `lift_resolution_exercised=False` | PASS |
| J8 `posthoc` 常设件（R639 12 跑次） | `rc≠0 ∧ stdout 逐字节正确` 条数 **0**（无跑次被低估） | PASS（该列由「不可判」转可判） |
| J9 确定性 | 5 组两跑逐例逐字节相同 | PASS |

**rc 分层（v4）**：`rc=2`（**器具层**，唯一抬 rc 项 = J6 v1 双红）；能力/次级栏 1 条（J4 未定因 4/5）。rc 未由能力面抬升，亦未由能力面掩盖器具面。

## 本轮核心产出一：缺口族**可执行前置步骤**（`eval/rover/r640/wythoff_precheck_r640.py`）

把「静默错步（用例通过数下降这一个标量）」变成「**事前可执行、逐谓词点名**的违规清单」——
7 个谓词在同一 25×25 网格上各自点名：`P0 预算 / P1 入口 / P2 格式 / P3 着法合法性 /
P4 状态 / P5 冷集自洽 / P6 字典序最小`。着法语义**逐例反解**自冻结题集样例
（`21 25 ⇒ WIN 15 15`、`10 9 ⇒ WIN 0 3`、`18 8 ⇒ WIN 5 0` ⇒ 皆指向必败位 `(6,10)/(6,10)/(8,13)`），
**非猜测**；真值仍取 r622 独立 oracle。

**四腿齿证（v2，全绿）**

| 腿 | 臂 | 期望 | 实数 |
|---|---|---|---|
| POS（真机） | 机取的 **6** 个全绿跑次 | rc=0 | **6/6 = rc 0** |
| NEG（真机） | 机取的 **6** 个失败跑次 | rc≠0 且逐谓词点名 | **6/6 = rc 1**（全部有名谓词） |
| 合成正控 | 真值跑次树副本 | rc=0 | **rc 0** |
| 合成变异 | 恒 `LOSE` | rc=1 | **rc 1** |
| 合成超预算 | 0.5 s/格 | rc=1（`P0_budget`） | **rc 1** |
| 合成器具 | 进程自杀（stdout 不可解析） | rc=2 | **rc 2** |

**逐跑次谓词读数（冻结面，v2）**

| 跑次 | 冻结分 | rc | 违规谓词（格数） |
|---|---|---|---|
| w237/agentP-r1 · w237/codex · w238/agentP-r1 · w238/agentP-r2 · w238/codex · w239/agentP-r3 | 15/15 | 0 | — |
| w237/agentP-r2 | 3/15 | 1 | `P4_state` 377 · `P5_coldset` 18 |
| w237/agentP-r3 | 12/15 | 1 | `P1_entry` 98 · `P5_coldset` 8 · `P6_lexmin` 67 |
| w238/agentP-r3 | 12/15 | 1 | `P3_legal` **134** · `P4_state` 113 |
| w239/agentP-r1 | 4/15 | 1 | `P4_state` 559 · `P5_coldset` 26 · `P6_lexmin` 5 |
| w239/agentP-r2 | 3/15 | 1 | `P4_state` 592 · `P5_coldset` 3 |
| **w239/codex（外部真值臂）** | 13/15 | 1 | `P3_legal` **204** |

## 本轮核心产出二：三条实质读数（均由「谓词网格」而非「15 例标量」暴露）

1. **外部真值臂自身**在 204/625 格给出**非法着法**（如 `21 25 ⇒ WIN 1 13`：相差 `(20,12)`，既非单堆取、亦非双堆等量取），
   而冻结的用例级判分只给 13/15 —— **15 例抽样对「系统性违法」分辨率不足**（抽样只覆盖 625 格里的 15 格）；
   这与 skill「题面-判据一致性 / 抽样分辨率」同族：**判据面必须与规格面同构**。
2. **机制词表比谓词面粗**：R637 判别式把该族归为 `COLD_SET_EQUAL` **8/12**，而谓词面显示
   `w238/agentP-r3`（冷集等价却 `P3_legal 134`）、`w239/codex`（冷集等价却 `P3_legal 204`）——
   **冷集正确 ≠ 着法合法**；单条判别式会漏掉「冷集对、着法错」这一整类。
3. **入口/预算维度可被独立点名**：`w237/agentP-r3` `P1_entry 98`（98 格抛异常，对应冻结面 2 例 `HARD_CRASH`）；
   `w239/agentP-r1` 的 625 格实测 **148.18 s**（v1 预算 120 s 下被读成「器具超时」）⇒ 预算必须与谓词**分栏**，
   否则「交付物过慢」会被静默归成器具缺陷。

## 自捕（本轮，逐条留痕，均不改历史判决）

1. **手写期望表 = 编造控制（v1 首红根因）**：v1 凭印象把 `w239/codex` 列入「全绿跑次」，而冻结面实测该真值 **13/15** ⇒
   POS 腿假红。修法 = 期望表**机取**（`out/attrib-r640.json.per_run_wythoff`），缺源即 `rc=3` fail-closed。
   **这是「期望表必须机取、禁硬编码」的一次现场实例**（与 skill「机取预注册/禁手抄」一致）。
2. **归层错误（v1 第二红根因）**：探针超时被归 `rc=2`（器具层），实为**交付物侧过慢** ⇒ 独立成谓词 `P0_budget`（rc=1，点名），
   rc=2 只保留「探针 stdout 不可解析 / 解释器失败」；合成「进程自杀」臂证明 rc=2 这一腿**仍有牙**。
3. **判定器影子自检抓到自身两处缺陷**（真机判决产出**之前**）：① S4 的翻面方向写反（把中位式改成更跨阈的 `−30`
   ⇒ 两式仍同向，断言恒假）⇒ 改为 `0`（不跨阈）后翻面成立；② S6 未先中和 J6 器具红 ⇒ 能力层读数被器具层掩盖（rc=2 而非 1）。
   两条均**先修器具再加真机读数**，未放宽任何断言。
4. **v1 器具字节与读数原样留存**：`eval/rover/r640/instruments/wythoff_precheck_v1_r640.py`
   （sha16 `f34c1cd7e856cb38` = v1 读数件 `instrument` 字段，已逐字核对）+ `out/precheck-r640-v1.json`；v2 另立命名空间。

## 诚实边界

- **只读复算面 ≠ 真机新跑** ⇒ 全部读数只对 **R639 冻结面**成立；本轮**不宣称生产已修**、不宣称任何降幅。
- **行级定因来自副本上的最小修复实验** ⇒ 只证「缺陷在被改那一行」，不证生产链路上只此一处；4 个失败跑次**未定因 = 未测到**，不是「无缺陷」。
- **无单变量轴 / 无新窗集 / 无新跑次** ⇒ **跨轮禁相减**（RF0005 §6 红线 4）；本轮不与 R639 的 `D=[−3,0,−9]` 做任何相减。
- **铁律 11 可执行前置器不适用**（无真机臂、无降幅宣称）—— 显式声明，不是跳步掩盖。
- **J8 posthoc 为 30 s 超时口径**（冻结跑 10 s）⇒ 只作**上界**读数。
- **`P3_legal` 的语义由题面样例反解**（`WIN i j` = 各堆取走枚数）；若未来题面改写该字段语义，本谓词须同步重钉。
- 三档终局目标读数（32 ms 级 / 快 50× / −95% / 成本 −85~91%）本轮**不动不宣称**。

## 下轮候选

1. **J4 未定因 4/5** 的补做：`w238/agentP-r3`（`P3_legal 134` 指向「着法枚举未限定合法着法」）与 `w239/codex`
   （`P3_legal 204`）属**同一新机制类**（冷集对、着法错）⇒ 对这两跑次做逐行最小修复实验，把该类从「未测到」变「已定因」。
2. **J6v2 重新预注册**（修正后的齿证规则与机取期望表进入 `prereg-r641.json`；v1 的 FAIL 不翻案、只标 `supersedes`）。
3. **判据面分辨率**：把「625 格谓词网格」与「15 例抽样」的**同构性缺口**登记为器具面条款候选
   （抽样族 = 规格面的稀疏子集 ⇒ 需声明抽样对哪类违规**原理上不可见**）。

## 门禁与读数背书

- **形式门禁 14/14** —— `env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q` ⇒ `Failed: 0, Passed: 14`（测试工程编译 **0 error**；**产品二进制跳步** —— 零产品源码改动 ⇒ 无被测件可构建）。
- `python3 eval/capability/status_gen.py --check` ⇒ **PASS（违规 0 / 基准漂移 0 / 缺源 0）** · `python3 eval/capability/decl_sweep.py --check` ⇒ **0 漂移（30 件）** · `roundcheck preflight --round R640` rc=0。
- **roundcheck 基线例外治理**：5 条 2026-09-09/14 时代条目（R609/R614/R618 记，`expires_round=R625`）**过期未清 ⇒ 回红**；因 R2/R6/R7/R8 在本轮实测均为 PASS（R6 = 26 文件 ≤ 40；R8 由本节读数补齐），按治理「唯一入口 `baseline --remove`」逐条**清除**（抑制只许减：`max_entries` 5 → **0**），清除后 `audit --round R640` **FAIL=0**。
- 通过率读数（供追溯）：oracle 正控 **15/15** · 前置器 POS 腿 **6/6** · NEG 腿 **6/6** · 合成四臂 **1/1/1/1** · 冻结面逐跑次 **12/12** 落 rc·谓词。
