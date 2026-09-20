# R598 轮志 — 判据 v3 **第六窗集**行使（真机臂轮 w178..w180）× 外部真值 codex + 只读并轮 候选②③④⑤

- 起手: 2026-09-20T19:01:23+08:00（`launch_r598.sh` 起手器 = own-tool 收口 + 起手）; 收轮: 2026-09-20T19:07:40+08:00
- 驱动器 `eval/rover/r598/run_r598.sh`（派生自 r597；**判据逻辑一字未改**，仅命名空间/窗号/余量源替换 — 24 项 fail-closed 断言全过）
- 单变量 = **窗集**（w178..w180）。被测件、题集、判据、夹具与 R585–R597 同 sha：
  - bin `4b70fd7cdb39f1c7…`（`artifacts/pub_r591/agenthost`），运行期 sha 前后一致（`bin-sha-check.json` stable=true）
  - taskset 逐字节同源，g1 题面 `516f3208963c6e66…`（2162→2182 chars 冻结），cases-r521 逐字节同源
- 臂: `C1` = codex 真值 ×1/窗；`R598D` = 产品默认档（三枚剂量键显式 unset）×3/窗
- 零产品源码改动 / 零新增夹具语义 / 零新增开关

## 1. 起手闸（候选⑤ 行使面）

| 项 | 值 |
|---|---|
| swing 源 | r597 同态在飞窗实测（`runs/r597/logs/run-samples.jsonl`, n=46, min 2723 / max 2806 ⇒ swing **83MB**） |
| 起手前 3 样本 | CEIL(min)=**2856MB**, spread=0MB（≤50MB 过） |
| 条款 | MARGIN := clamp(83, floor 60, cap 146) = 83；**REQ = 2650 + 83 = 2733**；cap_binding=**false** |
| 起手闸 A1/A2 | PASS（mem 2850 / 2876MB, REQ 2733） |
| 判别力成对控制 | 压制到 2688MB（带内 2650≤m<2733）：基础门槛 **PASS** ∧ 条款 **GATE_BLOCKED** ⇒ `true_discrimination=true, rc=0` |
| 起手闸 B | `exec_precondition --leak-selfcheck` rc=0 |

**本 tick 环境事件（如实登记，非判据改动）**: 首次采样 CEIL≈2765MB ⇒ CAP = 2765−2650−60 = **55MB < floor 60** ⇒ 条款 fail-closed（窗口不可开）。
处置 = 起手前清场：own-tool LSP 收口（release 177MB，`logs/reap.txt`: mem 2712→2889MB）+ `sync`/`drop_caches`（page cache 回收，无数据/状态改动）⇒ CEIL 2856MB ⇒ 窗口开启。
影响面 = MemAvailable 读数；被测量（真值/产品产出物与判分）不受影响。

## 2. 主判据 v3 第六窗集（C7）与六窗集并列（**跨窗集禁相减**）

判据文本/阈值与 R589 同源同值：有效窗 `中位 ≤ −0.34 ∧ 负号窗 ≥ ceil(有效/2)`（写死，非事后调）。

| 窗集 | 轮次 | 窗号 | 有效窗 | 中位 D_task | 负号窗 | pass |
|---|---|---|---|---|---|---|
| set1 | r585–r588 | w154–w165 | 9 | −0.6667 | 8 | True |
| set2 | r591 | w166–w168 | 1 | −0.6667 | 1 | True |
| set3 | r595 | w169–w171 | 2 | −0.5 | 2 | True |
| set4 | r596 | w172–w174 | 2 | −0.5 | 2 | True |
| set5 | r597 | w175–w177 | 1 | −0.3333 | 1 | False |
| **set6** | **r598** | **w178–w180** | **2** | **−0.3333** | **2** | **False** |

- **set6 判决 = 未成立（不达 PASS 形态）**: 中位 −0.3333 **距阈值 −0.34 差 0.0067**；方向面 neg 2/2 一致。
- C0: **w178 真值自败 56/58 ⇒ `unreliable`，不进配对、禁筛窗**；w179/w180 真值 58/58。
- 逐窗 D_task: w179 = −0.3333、w180 = −0.3333（产品 3 跑次中 2 跑次整题全对 ⇒ 2/3 − 1）。
- 族 all-pass 率（并列，禁相减）: `wythoff` set1 0.3889 / set2 0.4444 / set5 0.7778 / **set6 0.5556**；life/nim/sub set2/set5/set6 全 1.0（set1 0.9722）。
- 逐窗读数（`taskface-pool-r598.json`）: w178 真值 56 vs 产品 47/51/58；w179 真值 58 vs 产品 58/58/46；w180 真值 58 vs 产品 58/56/58。

## 3. 参照面 / 成本 / 步数（kpi_r598，**参考（未可验收）**）

- C1 用例级配对（v2 判决面已作废，只作同向参照）: D_list [0, 0]、中位 0.0、有效窗 2、pass=True。
- C2 成本三列（禁合并名义总量）: 产品 **17 调用 / 4,293 新算 / 39,556 completion**；真值 **48 / 25,636 / 20,462**。
  命中率（口径 = 中继 dump 时间轴）: v_all 0.98 / 0.95、v_incr 0.96 / 0.97。
- C6 步数面: 非空 9/9（pass）；`steps_executed` [14,7,7,7,7,13,7,13,14] vs `plan_steps_total` [14,7,10,11,10,14,11,14,14]。
- C5b 摆动/效应（历史四集 R585–R588，池化 n=9）: 中位效应 −5.5 ⇒ 摆动 > 效应 ⇒ **该轴非承重变量、定案关闭**（与 R597 同基准，未重算）。

## 4. 只读并轮

### 候选② 真值侧 wythoff 缺口归因（`truthgap_r598.py` → `truthgap-r598.json`，rc=0）

跨 r585..r598 共 **27 窗**（真值 ×1 + 产品 ×3）逐例只读普查，按预注册 C8 三态判：

- 真值失败**全部**落在 wythoff 族：**10/27 窗、38 例次**；life/nim/sub 真值失败 = **0**。
- 真值失败集合 **6 种（非常量）** ⇒ 按预注册判 **② 真值臂自身漂移**（不是恒定集合）。
- 「两侧失败集合逐字相同」窗 = **0** ⇒ 预注册 ①（题面/夹具嫌疑）**未现**。
- 系统性点（新读数）: 对 `wythoff#43-public + wythoff#57-hidden` 在第 **4 窗逐字重复**（r596 w173 / r597 w175、w176 / r598 w178）⇒ 真值臂对该二例有可复现弱点（非单窗噪声）。
- 次数面: 真值 38 例次 vs 产品（同族）282 例次 union ⇒ 同族两侧皆失，量级不同。
- 控制: NEG-A 确定性（同输入两读逐字节相同）=True；NEG-B 非平凡（非常量 ∧ 非全空）=True；POS 注入（w179 真值造 1 例失败）⇒ 分类 ③→① 改变=True；rc=0。
- 诚实边界: 只读诊断 ⇒ 不构成能力验收；**不改题面/夹具**（改动须用户放行）。

### 候选③ C7 负控选择面改制（器具缺陷修法，预注册 C9；先 v1 后 v2 披露）

- **v1 读数（保留，不覆写）**: `taskface-pool-r598.json` — 选择面 = **仅 agentD-r1 单臂** × 当前窗集 ⇒ set5/set6 `target_window=null`、`has_teeth=false` ⇒ `rc=2`（R597 自捕同源）。
- **v2 修法（`taskface-pool-r598-ncv2.json`）**: 选择面 = **全部产品跑次 agentD-r1..r3 × 当前窗集**；仍无靶 ⇒ 保留 fail-closed（新增 `no_target` 字段）。
- **判定面差异（除 C7/verdict 外全部字段逐位比对）: NONE（6 个窗集全过）** ⇒ 器具修法是中性的，未动任何阈值/判据文本。
- 靶点变化: set1 w155→w155、set2 w166→w166、set3 w169→w169、**set4 w173→w172**（两者皆有牙、判决不变）、set5 null→**w176**、set6 null→**w178**；set5/set6 `has_teeth` false→true、rc 2→0。
- `checks_posthoc`（**超出预注册范围，本轮不改，单列供下轮预注册**）: rc 与判据判定**脱钩** — v2 下 set5/set6 `rc=0`（"PASS"）而 `C1_task_face_v3.pass=False`（缺口未成立）⇒ rc 未编码验收面。本轮只记录，不动 rc 语义（事后加码禁止）。

### 候选④ V_int 第五窗集（`landing_predicate_r593.py --rounds r598 --codex-too`）

- agent: runs=9 桶 {`D_delivery_or_shape`:14, `A_selection_order`:2, **`B_coldset`:16**}，D 子桶 {`D3_move_illegal`:14}；层分布 {(c) 本轴外:6, (b) 冷集构造层:3}
- codex: runs=3 桶 {`D_delivery_or_shape`:2}，D 子桶 {`D3_move_illegal`:2}；层分布 {(c):3}
- 份额差（agent−codex）: A **+0.0625**、B **+0.5**、D **−0.5625**
- `V_int` 直方图: agent {0:7, 25:1, 35:1}；codex {0:3} ⇒ **阈值化仍未测**（预注册禁止设阈值/触发）
- 守恒=True、只读=True、残留 0/0
- **零回归=False 属单窗集 scope 伪影**（器具的零回归面钉在 R592 登记件上，`--rounds r598` 只覆盖 9 跑次 ⇒ 读法不成立）；历史全集（r585–r588+r591，跨 15 窗 60 跑次）复算：
  - `landing-hist-r598.json` (`rc=0`): `zero_regression.match=` **true** — buckets `{A_landing_loose 20, A_selection_order 6, B_coldset 184}`、layer `{(c)19, (b)22, (a)3}` 与 R592 登记件**逐位相同** ⇒ **器具完好**，r598 的 `零回归=False` 确证为单窗集读法伪影（R597 已一次、本轮第二次独立复现）。

### 候选⑤ 起手闸余量重派生
见 §1（swing 168→83，REQ 2775→2733，cap_binding true→false）。

## 5. 铁律 11 可验收前置（`exec_precondition.py --round r598`）

- `executable_and_correct=false`、`acceptable_scoped=false` ⇒ **rc=1**（`precond.rc`）
- **blocked 5 条**（R597 为 4 条），**全部**落 wythoff 族：
  - w178/agentD-r2 47/58、w178/agentD-r3 51/58、**w178/codex 56/58**（#43-public + #57-hidden）、w179/agentD-r3 46/58、w180/agentD-r2 56/58
- 逐窗 cases_pass: w178 {r1 58, r2 47, r3 51, codex 56}；w179 {58, 58, 46, 58}；w180 {58, 56, 58, 58}
- ⇒ **全部成本/质量读数标「参考（未可验收）」，禁作验收依据**
- 两处**既有**仪器噪声（与 R597 逐位同形，非本轮回归）: `undeclared_arms`=12、`claim_unmapped`=9（两轮同值）；`policy.active=false (no_policy_key)`。

## 6. 行为面契约普查（候选③ R597 口径延续，`behav-census-r598.json`）

- agent: 81 跑次 {OK 73, INTERNAL 4, **ENTRY_FAIL 2**, TIMEOUT 1, OTHER 1}；codex: 27 跑次 {**OK 27**}
- ENTRY_FAIL 2 例: `r588/w163/agentD-r2`、`r591/w166/agentD-r2`，报错同为 `AttributeError: module 'games.wythoff' has no attribute 'solve'`（与 R594 定因的产物侧契约自相矛盾同源）
- 控制: POS 有牙=True、NEG 干净=True、只读=True、残留=0 ⇒ rc=0

## 7. 逐例归因（`percase-attrib-r598.json`，rc=0）

- 27 窗 1566 例次；池化桶 {OK_两侧全过 1235, A2_摆动带 271, E_真值败_我方部分 30, **A_我方独败 22**, B_真值独败 6, C_两侧同败 2}
- 跨例交叉校验 equal=6262 / mismatch=0 / missing_side=0（issues 2）
- A 份额（池化）= **0.0140**（R597 单窗集为 0.0；两轮**并列不相减**）⇒ rc=0
- 控制: POS 有牙=True、NEG 确定=True、非平凡=True

## 8. 诚实边界

1. **铁律 11 rc=1** ⇒ 全部成本/质量读数「参考（未可验收）」。
2. set6 有效窗仅 2（w178 被真值自败剔除）⇒ 中位与摆动仍不可分离，**不作能力结论**（摆动 ≥ 效应纪律）。
3. 判据 v3 判决为「缺口未成立」与「产品 3 跑次中 2 跑次整题全对」并存 ⇒ 需按族（wythoff）与按例读，不可读成单一趋势。
4. 候选① 未做（待用户放行）⇒ 零产品源码改动。
5. `checks_posthoc` 两条（rc 与判据脱钩、landing 零回归单窗集 scope 伪影）**不得回写成预注册命中**。
6. 本 tick 起手前清场（reap 177MB + drop_caches）为环境处置，已登记；跨轮 **MemAvailable 读数不可直接比**。

## 9. 下轮候选 (R599)

① **产品侧处置裁定（待用户放行）**：落点已收束到 `wythoff` 冷集构造层（候选④ B 份额 +0.5）与产物侧入口契约（ENTRY_FAIL 2 例）；动 `src/` 须放行。
② **rc 语义收口（预注册）**：把验收面（`C1_task_face_v3.pass`）编入 rc（fail-closed），配历史判决审计证明「纯收紧、判决中性」。
③ **真值侧弱点面收口**：对 `wythoff#43-public + wythoff#57-hidden` 做文本级定因（真值臂产出 vs 期望），判「真值侧弱点」是否可由真值臂参数面（同件同档）解释。
④ `V_int` 第六窗集（随真机臂轮）+ landing 零回归面**钉到可复现 scope**（把 `--rounds` 与登记件 scope 绑成机检，消除单窗集伪影）。
⑤ 起手闸余量按 r598 实测振幅重派生（`runs/r598/logs/run-samples.jsonl`）。
