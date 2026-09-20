# R597 轮志 · 判据 v3 第五窗集行使（真机臂轮 w175..w177）+ 只读并轮（候选②③④⑤）

**单变量**: 无新轴 —— 与 R585–R596 **同被测件**（bin sha12 `4b70fd7cdb39`，stable=True）+ **同冻结题集**（`e0c667c2…`）+ 同判据（v3）；唯一改动 = 窗集 `w175..w177`（每窗 真值×1 ＋ 产品默认档×3）。候选①（产品侧修复）**待用户放行 ⇒ 零 `src/` 改动**。

## 主判据（判据 v3 第五窗集）

- set5: valid=1 / 中位 -0.3333 / 负号窗 1 ⇒ **不达 PASS 形态**（阈值 −0.34 写死；有效窗仅 1 ⇒ 判据无分辨率，不作能力结论）
- 有效窗塌缩根因: 真值自身未全对（w175 codex 56/58、w176 codex 56/58）⇒ 按预注册 C0 该两窗 unreliable 不进配对（禁筛窗）；w177 真值 58/58 有效，产品 [58,58,43] ⇒ D_task=-0.3333
- 并列集: set1 {valid 9, -0.6667, PASS} / set2 {1, -0.6667, PASS} / set3 {2, -0.5, PASS} / set4 {2, -0.5, PASS}（跨窗集禁相减）
- 按族 all-pass 率: life/nim/sub set5=1.0；**wythoff set5=0.7778**（set1 0.3889 / set2 0.4444 / set4 0.5556 —— 五窗集同向缺口面，禁相减）
- 器具自捕: pool C7 负控 has_teeth=False ⇒ rc=2（靶点选择面 = agentD-r1 单臂，set5 的 r1 三窗零失败例 ⇒ 结构性无靶；登记为器具缺陷，禁手改判据凑绿）

## 成本三列（铁律 11 rc=1 ⇒ 「参考（未可验收）」）

- 产品: 调用 18 / 新算 prompt 3719 / completion 39146（v_all 0.98 / v_incr 0.97）
- 真值: 调用 17 / 新算 prompt 12446 / completion 9536（v_all 0.92 / v_incr 0.94）
- 步数列 9/9 非空（steps [7,7,14,7,8,7,14,7,7] / plan [10,10,14,10,11,10,14,10,8]）

## 候选② 铁律 11 阻塞臂逐例归因（r597 单窗集，与 R596 池化面并列）

- 桶池化（w175..w177，174 例次）: {"OK_两侧全过": 155, "A2_摆动带": 15, "B_真值独败": 2, "E_真值败_我方部分": 2, "A_我方独败": 0, "C_两侧同败": 0}
- A 份额 = 0.0000（本轮我方独败为零）；跨例交叉校验 equal=696 / mismatch=0
- 控制面: POS skipped=「无 A 类例」（结构性无靶，非器具坏）· NEG 逐位确定=True · 非平凡=True（3 族签名互异）

## 候选③ 行为面契约普查（r597 增量）

- agent: {"runs": 9, "OK": 9} / codex: {"runs": 3, "OK": 3} —— ENTRY_FAIL/INTERNAL/TIMEOUT 全 0（历史 12 窗集累计: agent ENTRY_FAIL 2/63 不变）
- 控制: POS 有牙=True / NEG 干净=True / 只读=True / 残留=0 / rc=0

## 候选④ `V_int` 第四窗集分布（不设阈值）

- agent 桶 {"B_coldset": 15, "D_delivery_or_shape": 2} / 层 {"(c) 本轴外": 8, "(b) 冷集构造层": 1} / `v_int_hist` {"0": 8, "10": 1}
- codex 桶 {"D_delivery_or_shape": 4} / 层 {"(c) 本轴外": 3}
- 零回归面: r597 单窗集 scope 上 match=False 属**结构性不适用**（登记基准 = r585..r591 的 44 跑次）；同器具对历史全集复算 **match=True**（buckets/layer 逐位复现，/tmp/lp_zr_check.json 已并入本读数档案）⇒ 器具完好；守恒=True / 只读=True / 残留=0

## 候选⑤ 起手闸余量条款

- 余量源 = r596 同态在飞窗实测振幅 **168MB**（n=61, min=2454/max=2622）；ceiling=2835 / spread=4MB / margin=125 / REQ=2775 / cap_binding=True ⇒ 起手闸 A1/A2 连续 PASS（mem 2850/2857 ≥ 2775）

## 铁律 11 前置器

- rc=1：`executable_and_correct=False` / `acceptable_scoped=False`；blocked=4 条（w175/codex 56/58、w176/agentD-r3 56/58、w176/codex 56/58、w177/agentD-r3 43/58 —— 全部落 wythoff 族）

## 诚实边界

- 铁律 11 rc≠0 ⇒ 全部质量/成本读数标「参考（未可验收）」，不宣称任何降幅/增益；
- set5 有效窗仅 1 ⇒ 判据 v3 无分辨率，本轮**不得**作「缺口消失/收窄」结论（与 set3/set4 同纪律）；
- 候选②③④ 为只读/聚合面 ⇒ 不构成能力验收；跨轮/跨窗集禁相减；候选①（产品侧修复）待用户放行。
