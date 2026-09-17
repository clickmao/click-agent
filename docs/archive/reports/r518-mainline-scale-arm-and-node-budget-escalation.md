# R518 — 编排节点预算自适应(②) + 生成器契约负控(③) + 双包规模面三臂对照(①) · 2026-09-17

轮号: R518 | 主线: 外部真值对照 (§0-0 铁律 10) | 前置器: `exec_precondition --round R518` **rc=1 ⇒ 对比读数一律标「参考(未可验收)」**

## 一、本轮四项候选 (全部推进, 禁单步)

### ② 编排节点**预算自适应** (真实链代码改动)
- 事故链: R517 编排臂 n3 以 6 步判 `no_artifact`(假绿防护生效) ⇒ 整链断; 单节点预算写死 ⇒ 「整合型节点」永远缺步。
- 改动 (`src/agent/intent/TaskOrchestrator.cs`): `Options.MaxBudgetEscalations` (L60, 0..3, 缺省 **0** = 旧行为逐字不动); 升预算重试环 (L~295-310): 仅**远端**节点、仅 **`no_artifact`** 违规触发, 预算 `min(32, 2×)`, 上界 `MaxNodeBudget`(L139); 重试前撤销同因记账 (防重复计数); 遥测新增 `BudgetSteps/Escalations/Attempts`(L182 起), `BudgetCeilingEffective`/`EscalationCount`(L179/182); 宿主 CLI `--node-escalations` (`OrchestrateCommand.cs` L46, 缺省 **1**) + 报告新字段 `budget_steps/escalations/attempts/budget_ceiling_effective/node_escalations_max/escalations_total`(L328-330,357)。
- 单测 (`src/agent.tests/TaskOrchestratorBudgetTests.cs`, 12 例): 升预算后成功 / 越界不掩盖(负控) / 重试有界 / 缺省关闭前态锚 / 封顶 32 / 本地节点不升 / 同因只记一条。
- **真机liveness** (`/tmp/r518/orch-0917-132218/orch/report.json`): n3 `attempts=['6:Failed','12:Completed']` `budget_steps 6→12` ⇒ **该次重试直接决定了 tasksvc 整包 12/12**; q1 两次(6/12)仍 `no_artifact` ⇒ 诚实上界: 一次升预算不足 (预算上界 24→36)。

### ②′ 运行期缓存排除 (真机自抓的链缺陷, 同轮修)
- 事故链: 节点按题面「写自测并**运行**」⇒ 解释器自动落 `tasksvc/__pycache__/*.pyc` ⇒ 旧 diff 判其 `out_of_scope` ⇒ 整链 fail-closed (节点真实产物 cli.py 尚未写就被判死, `run-0917-131155`)。
- 改动: `IsRuntimeCache` (L399) 只排除字节码/缓存目录 (`__pycache__`/`.pytest_cache`/`.mypy_cache`/`.ruff_cache`/`*.pyc`/`*.pyo`), 源码与数据文件照旧进范围契约。
- 单测 (`TaskOrchestratorCacheFilterTests.cs`, 4 例): 正控 (缓存不判越界) + **负控 3 条** (真实越界仍判死 / 只有缓存仍算零产物 / 同名 `.pyc` 排除而普通文件不排除)。

### ③ 生成器回归负控 (R517 事故防复现)
- 器具: `eval/rover/r518/check_plan_contract.py` (镜像判据 P1-P9/S1-S8 + H1 远端覆盖) 与 `gen_plan_r518.py` (**生成即机检, 非法不落盘**; 落盘后回读再检)。夹具保真闸: 节点文本必须以题面原文结尾 (禁改写字符, 含 `|`)。
- **负控读数 (12 变异 × 双源)**: 每条变异 **镜像报红 ∧ 真二进制 `--orchestrate` 校验期 rc=2 拒收** 全部 PASS (`NC_ALL_PASSED=True`); 变异有效性自检 (文本未变 ⇒ 判 FAIL) 以防空转。含 R517 事故本体 (`S2 范围重复声明`)。
- 起臂前门: `gen_plan_r518.py --check` ⇒ `PLAN_ON_DISK_CONTRACT_OK`; `build_taskset_r518.py --check` ⇒ 题面 sha/prompt 逐字节未动。

### ① 双包规模面三臂对照 (窗口 w2, 同环境·同输入·同模型)
题面: p3 kvsvc (12 隐藏用例) + p4 v2 tasksvc (12 隐藏用例), 两侧 prompt sha `efa48cb2…`/`384fa721…` 与入库值一致; 起手闸 2×PASS。

| 臂 | 隐藏用例 | 远端调用 | prompt_tok | cached | completion | total_tok | 用时 |
|---|---|---|---|---|---|---|---|
| A 本侧单轮 (默认预算) | **24/24** | **13** | 130,185 | 117,120 | 13,021 | **143,206** | 51.9 s |
| C codex (外部真值) | 21/24 | 36 | 486,318 | 463,744 | 14,889 | 501,207 | 128.7 s |
| 比 (A/C) | 1.143 | **0.361** | 0.268 | — | 0.875 | **0.286** | 0.40 |

- 编排臂 O (7 节点: 5 远端 + 2 本地自测): 6/7 节点完成, 预算上界 24→36, 升预算 2 次; **tasksvc 12/12**, kvsvc 0/12 (q1 两次零产物 ⇒ q2/q3 跳过)。
- **主线判据读数 (标「参考(未可验收)」)**: 远端调用数 ↓**63.9%**, total token ↓**71.4%**, 新增 prompt ↓42.1%, 质量 **24/24 vs 21/24** (codex 在 p3 丢 3 条: `incr_semantics_and_409`/`incr_concurrent_atomic`/`restart_drops_expired`)。R413 的「≥30%」在**调用数与总 token 两个量上都达标**。
- **规模面结论 (反 R515 假设)**: 本侧**单轮**(默认预算) 已覆盖双包 24 用例 ⇒ 「双包超出单轮硬顶」在此规模**不成立**; 编排器的必要性在本轮**未被证明**, 但其预算自适应在 n3 上**救回了整包正确性**。

## 二、铁律 11 前置器 (收口)
- `python3 eval/rover/r507pre/exec_precondition.py --round R518` ⇒ **rc=1** (`ACCEPTABLE_SCOPED=False`): 要求面 = `w2/agentA`(12/12,12/12 ✓) + `w2/codex`(**p3 9/12 ✗**)。
- ⇒ 本轮 token/调用降幅**一律标「参考(未可验收)」**(规则要求, 即使降幅远超阈值且质量不降)。
- 会话内自抓并修正两处**范围模式语法**(匹配键 = `<窗>/<臂目录>`, 不含题号; 旧写法 `w2/agentA/*` 致 `UNDECLARED`) ⇒ 修正后 `SELF_REPORT_AGREES=True`, 要求/非要求臂集合与判据**未变**。

## 三、诚实边界
1. **reps=1**: 外部真值 codex 在同一 p3 题面上跨跑次**方差显著** (w1 12/12 → w2 9/12) ⇒ 「两侧均正确」的验收前提在单跑次下不稳定, 对比**不作验收依据**。
2. **w1 整窗作废** (留痕不删): 器具两缺陷 —— 臂 A 未 `export AGENTFRAMEWORK_CONFIG` ⇒ 请求绕过计量 adapter (未计量真实调用**已发生**, 读数不可用); 编排臂 `cwd` 落在节点工作区内 ⇒ 宿主自写 `data/**` 被判越界 ⇒ 链 fail-closed。
3. 编排臂 token **禁与单轮臂混算** (输入粒度不同: 按段切分)。
4. 未测: reps≥3 重测、q1 类节点升预算上限 2 的效果、并行(prefork)编排窗口内的归属唯一性。
5. `improvements.md` **R517 轮节仍缺** (对侧/前一轮遗留, 本轮不代写, 记结转)。

## 四、下轮候选 (R519)
① 对比读数**稳健化**: 以「远端调用数下降」为主判据 + reps≥3, 并预声明 codex 侧跨跑次波动为噪声源;
② q1 (kvsvc 第 1 段) 零产物定因: 分段切分/提示词 vs 预算; 试 `--node-escalations 2`;
③ 生成器契约机检**接入所有轮脚本** (R519 起为硬前门);
④ R517 轮节回填 + R404-R407 结转;
⑤ 编排臂并行窗归属唯一性 (多层并发) 真机验证。
