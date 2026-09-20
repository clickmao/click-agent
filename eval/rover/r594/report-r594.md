# R594 轮志 — 入口契约面只读定因（候选②）+ 面读数并轮（候选③④⑤）

**轮次性质**：只读定因并轮。零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关。
**被测对象**：在盘快照树（59 跑次 × 4 模块）+ 冻结用例集 `cases-r521.json`（逐字节不变）。
**预注册/DAG**：`eval/rover/r594/{prereg-r594.json,dag-r594.md}`（起手前落盘）。

## 候选② 入口契约面（决定性读数）

| 面 | 读数 | 器具 |
|---|---|---|
| 题面 | 要求 `solve(text: str) -> str` = **True**；评分路径 `python3 -m games` ×2 | `entry-contract-r594.json::face_statement_vs_judge` |
| 判分器 | 实发 argv `-B -m games`（同源）∧ **无**直接导入 | 同上（源码抽取，非人工） |
| 两侧 census | agent **2/44** 跑次缺 `solve`（均仅 `wythoff`）vs codex **0/15** | `sides` / `missing_runs` |
| 实测复现 | 2 跑次 rc=1 ∧ stderr 尾行 `AttributeError: module 'games.wythoff' has no attribute 'solve'`；对照跑次 rc=0 | `replay` |

**裁定**：`branch_product_contract = True` / `branch_fixture_defect = False` ——
两个缺入口跑次**自己的** `__main__.py` 都调用 `.solve`（`main_calls_solve=true`）而其**自己的** `wythoff.py`
只定义 `_win`/`_lose`（无 `solve`）⇒ **产物自身契约自相矛盾**；题面已写明入口名、判分路径与题面同源 ⇒
题面/夹具分支被**否证**；两侧同败强判据（codex 侧 0/15）**不成立** ⇒ 不判夹具/题面缺陷。

## 候选③④⑤ 面读数（纯聚合，零子进程）

- **③ `V_int` 按窗集分层**：15 个窗集 × 两侧直方图落盘；交叉校验 `cold_set_equal ∧ V_int>0` = **0/59**；
  2×2 列联：agent `(T,0)=19 / (F,pos)=19 / (F,0)=6`、codex `(T,0)=11 / (F,pos)=4` ⇒
  **V_int>0 恒伴随冷集不等**（两侧皆然）。**阈值化 = 未测**（需新跑次）。
- **④ codex 独有 (b) 窗 `w154`**：codex 声明冷集 **51** vs 真值 **10**（多 41，形如整行 `(0,1..6)` 被判冷）⇒
  层 `(b) 冷集构造层`、13/15 通过、2 例 `B_coldset`；同窗 3 个 agent 跑次全 **15/15** 且层 `(c)` ⇒
  **该窗缺口属 codex 侧，非我方缺陷**（`codex_only_b_holds = True`，逐字段复算与登记层一致）。
- **⑤ 形态族集中度**（预注册机械规则：top-run 份额 ≥ 0.5 ⇒ 集中）：5 族中 **4 族集中**、
  1 族（`TypeError: 'NoneType'...`，n=11 / 4 跑次，份额 0.455）**散布** ⇒
  「执行面崩溃/挂死」形态**按跑次成簇**（`AttributeError` 30 = 2 跑次、`TIMEOUT` 8 = 1 跑次、
  `%d format` 2 = 1 跑次），不是跨跑次普遍形态。

## 零回归 / 只读性 / 器具自捕

- **零回归对照臂**：由同一件 R593 在盘 JSON 重算 A/B 级桶（`B_coldset 184 / A_landing_loose 20 /
  A_selection_order 6`）、层分布（`(b)22/(c)19/(a)3`）、`d_subs`（`D1 66 / D3 3`）、两侧 `V_int` 直方图
  ⇒ 与该轮登记值**逐位复现**；另断言 `D_delivery_or_shape == d_total = 69`。
- **只读性**：59 跑次快照树（`g1` 子树 `.py`）+ 冻结用例集 sha256 前后一致（`411434e5f8939c3b`）；
  控制只写 `/tmp` 副本。**确定性 ×2** 逐位相同。
- **器具自捕 2 件（零判据放宽、首跑留档不翻案）**：
  ① `entry_contract_r594` v1 **路径层级错**（census 传 `g1` 而非 `g1/games`）⇒ 全跑次「全 missing」，
  与同轮 POS 控制**直接矛盾**；修法 = **单点路径构造** + 新增「非平凡性」机检（全跑次面须有 present 模块），
  留档 `entry-contract-r594-v1pathbug.json`；
  ② `face_readings_r594` 首跑**打印面 KeyError**（读数面键名与打印面键名分叉）⇒ 修打印面不改读数面，
  留档 `face-readings-r594-v1printbug.json`；扩展 2×2 列联前的中间版留档 `face-readings-r594-v2.json`。

## 门禁 / 铁律 11

- **形式门禁**：`dotnet test … --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒
  **Failed 0 / Passed 14 / Skipped 0**。
- **铁律 11**：`python3 eval/rover/r507pre/exec_precondition.py --round r594` ⇒ **rc=3 DISCOVER_FAIL**
  （零新臂 ⇒ 前置器不适用）⇒ **不作任何降幅/增益宣称；tokens 三列 = 未测**。
- 零 `src/` 改动、零登记表改动 ⇒ 依 R588–R593 同处置**不造** capability 登记行。

## 诚实边界

1. 只读产物诊断 ⇒ **不构成能力验收**，不得回写成「产品已修」；
2. 候选②的 2 个缺入口跑次属**产物侧**契约自相矛盾，但**产品侧修复仍待用户放行**（候选①）；
3. `V_int` **阈值化未测**（需新跑次），本轮只出分布与列联；
4. 形态族集中度为**跑次级**统计（44 agent 跑次横跨 5 窗集）⇒ 非独立样本；
5. 跨轮**禁相减**：R593 读数只用于零回归对照臂的逐位复现；
6. `w154` 的 (b) 属 codex 侧 ⇒ 不得计入我方缺陷份额。
