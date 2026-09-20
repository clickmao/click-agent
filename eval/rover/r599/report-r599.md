# R599 轮志 — 判据 v3 **第七窗集**行使（真机臂轮 w181..w183）× 外部真值 codex + 只读并轮 候选②③④⑤

- 起手: 2026-09-20T20:48:10+08:00（含 own-tool reap + sync/drop_caches 清场）; 收轮: 2026-09-20T20:53:25+08:00
- 单变量 = 窗集；被测件 sha `4b70fd7cdb39`（`artifacts/pub_r591/agenthost`）、题集 sha `e0c667c2a313c04b`（g1 题面 sha 已钉）、
  夹具 `cases-r521` 冻结件与 R585–R598 **同 sha** ⇒ 只换窗集（判据 v3 第七窗集）。
- 臂: `C1` = codex 真值（side=codex，reps 1/窗）; `R599D` = 产品默认档（三枚剂量键显式 unset，reps 3/窗）。

## 1. 起手闸（候选⑤ 行使面）

- 余量源 = `runs/r598/logs/run-samples.jsonl`（n=57, min 2589 / max 2853MB）⇒ `prev_swing_effective=264`
  （**口径诚实**: 该窗含 R598 环境事件 CEIL 2765→2889MB ⇒ 264 是保守方向）。
- 起手前 3 样本 CEIL 2889MB / 极差 25MB（≤50MB 门内）⇒ CAP = 2889−2650−60 = 179 ⇒ MARGIN = clamp(264,60,179) = **179**
  ⇒ REQ = 2829（`cap_binding=true` ⇒ 振幅项退化，收紧的是上界；与 R598 同形，已登记）。
- 起手闸 A1/A2 两次 **PASS**（mem 2903 / 2909MB）；判别力成对控制 **rc=0**（压制量 0 ⇒ 未行使，如实登记）；
  起手闸 B `leak-selfcheck` **rc=0**。
- 起手前清场登记（**环境动作，非判据改动**）: reap 本会话按需工具子进程 LSP ×2（RSS 248088kB + 3872kB）+
  `sync` + `drop_caches` ⇒ MemAvailable **2629 → 3000MB**（前后差已记；无数据/状态改动）。

## 2. 判据 v3 第七窗集（主判据, 器具 `pool_taskface_r599.py`, set7 新增）

- **set7(w181-183): valid=`0` / median=`None` / neg=`0` / pass=`False` / verdict=`不可判`** ⇒
  **判据无分辨率，本轮不作任何能力结论**（真值三窗自败按 C0 全部剔除，禁筛窗）。
- 逐窗逐臂 cases_pass（前置器独立物化 + 真跑）:

| 窗 | codex 真值 | agentD-r1 | agentD-r2 | agentD-r3 |
|---|---|---|---|---|
| w181 | 56/58 (rc=1) | **58/58** | **58/58** | 47/58 (rc=1) |
| w182 | 51/58 (rc=1) | **58/58** | 56/58 (rc=1) | 47/58 (rc=1) |
| w183 | 56/58 (rc=1) | **58/58** | **58/58** | 46/58 (rc=1) |

- 参照面（`kpi_r599` C1，用例级配对，v2 判决面已作废 ⇒ 只作同向参照）: `valid_windows=0`、`D_median=null`、
  `truth_all_pass={w181:false,w182:false,w183:false}`；产品逐窗中位 58 / 56 / 58 vs 真值 56 / 51 / 56。
- 族 all-pass 率（wythoff；**跨窗集禁相减、只并列**）: set1 0.3889 / set2 0.4444 / set5 0.7778 / set6 0.5556 / **set7 0.5556**；
  life/nim/sub 各 set 均为 1.0（set1 为 0.9722）。
- set5/set6 复算（并列件）: set5 valid 1 / median −0.3333 / pass False；set6 valid 2 / median −0.3333 / pass False。

## 3. 成本三列（信息项，不判红绿；命中率口径 = 中继 dump 时间轴）

| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all | 命中率 v_incr |
|---|---|---|---|---|---|
| R599D（产品默认档, 9 跑次） | 18 | 4,127 | 40,617 | 0.97 | 0.97 |
| C1（codex 真值, 3 跑次） | 25 | 15,522 | 12,001 | 0.93 | 0.95 |

- 步数面（C6）: 产品 9 跑次 `steps=[7,7,10,15,11,6,7,7,7]`（中位 7）、`plan_steps_total=[11,10,14,15,12,6,11,10,14]`。
- **全部成本/质量读数标「参考（未可验收）」**（铁律 11 前置器 rc=1，见 §5）。

## 4. 候选② rc 语义收口（预注册 C11, 器具缺陷修法）— `rc-semantics-r599.json`, rc=0

- 规则: `rc=0 iff (C0.pass ∧ C7.has_teeth ∧ C1_task_face_v3.pass)`；否则 3(数据/真值) > 2(器具缺陷) > 1(验收面未达) 取首因。
- **器件 == 公式**: 7/7 窗集一致（`device_formula_mismatch=0`）⇒ 器件真按预注册公式落 rc（非自证）。
- **翻转（同读数、只换公式）**: tightening **3**（set5/set6/set7: 旧 0 → 新 1），relaxation **0** ⇒ **纯收紧**。
  （R598 checks_posthoc 登记的同源缺陷: 旧式 rc=0 而验收面 pass=False ⇒ 本轮收口。）
- 三例影子负控: ①旧0∧面True⇒0 ②旧2∧面True⇒2（不放松）③旧0∧面False⇒1（收紧生效）= 全过；
  在盘历史件交叉校验逐件入档（`hist-judgment-audit-r599.json`）。

## 5. 候选③ 真值侧两例**文本级定因**（`truthgap2_r599.py` → `truthgap-r599.json`, rc=0）

- 复现实例 **40** 个（codex 14 / 产品 26），**全部判 `semantic`**（无 format、无未复现）:
  - `wythoff#43-public`: 实得 `WIN 1 13` vs 期望 `WIN 15 15`（r596 w173 / r597 w175,w176 / r598 w178 / r599 w181,w183 逐字重复；w182 = `WIN 3 14`）
  - `wythoff#57-hidden`: 实得 `WIN 2 11` vs 期望 `WIN 25 25`（同上；w182 = `WIN 7 14`）
- 控制: NC-D 确定性=True、NC-T 非平凡=True、POS 翻面=True ⇒ **真值臂自身可复现弱点**（非题面/夹具；非格式差异）。
  诚实边界: 只读诊断，不改题面/夹具/真值臂参数（改动须用户放行）。

## 6. 候选④ `V_int` 第六窗集 + landing 零回归面 scope 绑定机检

- `landing_predicate_r593.py --rounds r599 --codex-too`（同一件定因器）: 跑次 12/12、oracle 一致=True、守恒=True、只读=True；
  - agent 桶 {`B_coldset`:21, `A_landing_loose`:11, `D_delivery_or_shape`:4}（D 子桶 `D3_move_illegal`:4）；
    codex 桶 {`D_delivery_or_shape`:8, `A_landing_loose`:2, `B_coldset`:1}；份额差 B **+0.4924** / D **−0.6162** / A **+0.1238**。
  - `V_int` 直方图: agent `{0:7, 118:1, 6:1}`、codex `{0:3}` ⇒ **阈值化仍未测**（预注册禁止设阈值/触发）。
  - 层分布: agent `{(c)6, (b)2, (a)1}`、codex `{(c)2, (b)1}`。
- 器具自身 rc=2、`零回归=False` ⇒ 经 scope 绑定机检判定为**单窗集读法伪影**（见下），不计入本轮结论。
- scope 绑定机检（`scope_bind_r599.py`, **外包机检，未改共享器具内部**）: 见 §6b。

## 6b. landing 零回归面 scope 绑定（候选④-b）— `scope-bind-r599.json`, **rc=3（BLOCKED）**

- 请求轮集 `[r599]` 与登记全 scope `[r585,r586,r587,r588,r591]` **不相交** ⇒ 按**预注册原样**判
  `blocked(unregistered_scope)`、rc=3 ⇒ 该面本轮**不可判**（既不是「回归」也不是「过」）。
  **预注册 C13 分类面缺「新轮集（不相交）」一类 = 设计缺陷**；正确形态单列 `checks_posthoc`
  （`⊂ 登记 ⇒ not_applicable(partial_scope)`；`∩ 登记 = ∅ ⇒ not_applicable(out_of_registered_scope)`；混合 ⇒ rc=3），留 R600 预注册。
- **器具中性证据（两条独立路径一致）**: 本 tick 全 scope 复算 59/59 跑次、oracle 一致 ⇒ 器具自身
  `zero_regression.match=**True**`，且其 `actual` 与 R598 在盘件 `landing-hist-r598.json` 的 `actual` **逐位相同**
  （`{A_landing_loose 20, A_selection_order 6, B_coldset 184}` / `{(a)3,(b)22,(c)19}`）⇒ 单窗集读法伪影确已定位，器具无回归。
- 器具自捕（本轮第 3 号）: 首版机检把登记件（r592，**不含** `zero_regression` 键）当含 `expected` ⇒ 读到空 dict ⇒
  中性证明恒否（**假红**）；修正为「读器具自身 match ∧ 与 R598 在盘件 actual 交叉比对」后转真（未放宽任何判据）。
- 影子自检四态全过（partial⇒不适用 / full⇒适用 / 未登记⇒rc=3 / 注入漂移⇒必报 mismatch）。

## 7. 行为面普查 + 逐例归因（只读并轮）

- `behav-census-r599.json`（rc=0）: 跑次 120（r585..r599）；agent 90 = OK 82 / ENTRY_FAIL 2 / INTERNAL 4 / TIMEOUT 1 / OTHER 1；
  codex 30 = OK 30。ENTRY_FAIL 二例均为 `AttributeError: module 'games.wythoff' has no attribute 'solve'`（r588/w163、r591/w166）。
- `percase-attrib-r599.json`（rc=0）: 窗口 30 / 例次 1740；桶池化 `{OK 1374, A2摆动带 295, E真值败我方部分 40, A我方独败 22, B真值独败 7, C两侧同败 2}`；
  跨例交叉校验 equal=6958 / mismatch=0；控制 POS=True / NEG=True / 非平凡=True；**A 份额 0.0126**。

## 8. 铁律 11 可验收前置（`exec_precondition.py --round r599`）

- `executable_and_correct=false`、`acceptable_scoped=false` ⇒ **rc=1**（`precond.rc`）
- **blocked 7 条（R598 为 5 条）全部落 wythoff 族**: w181/{agentD-r3, codex}、w182/{agentD-r2, agentD-r3, codex}、w183/{agentD-r3, codex}
- ⇒ **全部成本/质量读数标「参考（未可验收）」，禁作验收依据**
- 既有仪器噪声（与 R598 逐位同形，非本轮回归）: `undeclared_arms`=12、`claim_unmapped`=9；`policy.active=false (no_policy_key)`。

## 9. 诚实边界 / `checks_posthoc` / 器具自捕

1. **set7 有效窗 = 0** ⇒ 主判据「不可判」；产品侧逐窗中位高于真值（58/56/58 vs 56/51/56）**不得**读作能力提升
   （真值自败窗被剔，剩下面为 0 ⇒ 无分辨率）。产品侧处置仍未做（候选① 待用户放行 ⇒ 零产品源码改动）。
2. `checks_posthoc` 三条（**不得回写成预注册命中**）:
   - C11 把「有效窗 = 0（真值全窗不可靠）」编码为 `rc=1`（验收面未达）而非 `rc=3`（数据残缺）⇒ 语义升格留 R600 预注册；
   - C13 分类面缺「新轮集（与登记 scope 不相交）」一类 ⇒ 本轮按预注册原样判 BLOCKED(rc=3)，正确分类留 R600 预注册（见 §6b）；
   - scope 绑定以**外包机检**实现（未下沉进 `landing_predicate_r593.py` 内部）⇒ 下沉与声明刷新留 R600。
3. 器具自捕（本轮）: ①`pool` 回填 juxtaposition 时**覆盖原块** ⇒ 首跑 rc=1 未落盘 ⇒ 已改 twin 拼接 + 双键断言；
   ②派生件 `behav_census`/`percase_attrib` 被命名空间替换造成 **r596/r598 错标** ⇒ 已显式补丁归位并加断言；
   ③**面在飞冻结**：run/kpi/prereg 三件在飞行期间的 sha 与收轮后逐字节相同（本轮编辑只落在**非在飞面**）。
4. 起手闸余量 264 取自含环境事件的窗 ⇒ 偏保守（fail-safe 方向）；`cap_binding=true` ⇒ 振幅项退化（上界收紧）。
5. 上游 `pkill/pgrep -f` 自匹配坑本轮再现：`pgrep -f 'pyright-langserver'` 命中自身命令行 ⇒ 命令整段被 SIGTERM；
   改用括号技巧 `[p]yright-langserver` 并已重取读数。

## 10. 下轮候选 (R600)

① **产品侧处置裁定（待用户放行）**：落点收束在 `wythoff` 冷集构造层（候选④ B 份额 +0.49）与 `agentD-r3` 反复出现的
   交付面/入口契约（ENTRY_FAIL 2 例: `games.wythoff` 无 `solve`）；动 `src/` 须放行。
② **C11 rc 语义再分层**（预注册）：`有效窗=0` ⇒ `rc=3`（数据/真值不可靠）而 `验收面未达` 保留 `rc=1`；配历史回放。
③ **scope 绑定下沉**：把 scope 绑定机检并入 `landing_predicate_r593.py`（含器具声明刷新 + 全 scope 零回归复算）。
④ 判据 v3 **第八窗集**（真机臂轮 w184..w186，同件同题集）。
⑤ 真值侧弱点面**参数面收口**：对 `#43-public/#57-hidden` 试真值臂参数面（同件同档）以判「弱点可否被参数解释」（须先预注册）。
