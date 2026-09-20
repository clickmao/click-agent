# R596 轮志 · 判据 v3 第四窗集行使（真机臂轮 w172..w174）+ 只读并轮（候选②③④⑤）

**单变量**: 无新轴 —— 与 R585–R595 **同被测件**（bin sha12 `4b70fd7cdb39`，stable=True）+ **同冻结题集**（`e0c667c2…`）+ 同判据（v3）；唯一改动 = 窗集 `w172..w174`（每窗 真值×1 ＋ 产品默认档×3）。候选①（产品侧修复）**待用户放行 ⇒ 零 `src/` 改动**。

## 主判据（判据 v3 第四窗集）

- set4: valid=2 / 中位 -0.5 / 负号窗 2 ⇒ **PASS**（阈值 −0.34 写死）
- 并列集: set1 {'valid': 9, 'median': -0.6667, 'neg': 8, 'pass': True} / set2 {'valid': 1, 'median': -0.6667, 'neg': 1, 'pass': True} / set3 {'valid': 2, 'median': -0.5, 'neg': 2, 'pass': True}（**跨窗集禁相减**）
- 按族 all-pass 率: {"life": {"set1": 0.9722, "set2": 1.0, "set4": 1.0}, "nim": {"set1": 0.9722, "set2": 1.0, "set4": 1.0}, "sub": {"set1": 0.9722, "set2": 1.0, "set4": 1.0}, "wythoff": {"set1": 0.3889, "set2": 0.4444, "set4": 0.5556}}

## 成本三列（铁律 11 rc=1 ⇒ 「参考（未可验收）」）

- 产品: 调用 19 / 新算 prompt 4190 / completion 46389（v_all 0.98 / v_incr 0.98）
- 真值: 调用 38 / 新算 prompt 24802 / completion 16819（v_all 0.94 / v_incr 0.96）

## 候选② 铁律 11 阻塞臂逐例归因（只读）

- 桶池化（6 轮窗集全量）: {"OK_两侧全过": 933, "A2_摆动带": 231, "E_真值败_我方部分": 26, "A_我方独败": 22, "B_真值独败": 4, "C_两侧同败": 2}
- A 份额（= 加厚 prompt/契约类改动的**收益上界**）: 0.0181；控制 POS 有牙=True
- 跨例交叉校验（前置器 failed 集 ↔ `cases.txt` FAIL 集）: {"equal": 4870, "mismatch": 0, "mismatch_explained_partial": 2, "missing_side": 0}

## 候选③ 交付物行为面契约普查（替代 R595 静态面无牙版）

- agent: {"runs": 63, "ENTRY_FAIL": 2, "INTERNAL": 4, "TIMEOUT": 1, "OK": 55, "OTHER": 1}
- codex: {"runs": 21, "ENTRY_FAIL": 0, "INTERNAL": 0, "TIMEOUT": 0, "OK": 21, "OTHER": 0}
- 控制: base=r585/w154/agentD-r1 POS 有牙=True NEG 干净=True；只读=True

## 候选④ `V_int` 第三窗集分布（不设阈值）

- agent 桶 {"B_coldset": 31, "A_landing_loose": 7, "D_delivery_or_shape": 6} / 层 {"(c) 本轴外": 5, "(b) 冷集构造层": 3, "(a) 落点/选择谓词层": 1} / `v_int_hist` {"0": 6, "350": 1, "102": 1, "25": 1}
- codex 桶 {"D_delivery_or_shape": 2} / 层 {"(c) 本轴外": 3}
- 零回归（对 r592 池）：match=5 窗集零回归臂未收口（本 tick 时间预算内未跑完 ⇒ 不伪造 match）；r596 单窗集那次 match=False 属**结构性不适用**（登记基准 = 44 跑次，单窗集只有 12 跑次）⇒ 该次 rc=2 由零回归面产生，其余面（守恒/只读/无残留/控制 POS(a)·NEG(b)/oracle 一致）全绿；固有成员零漂移由 pool `reproduced_first_set` 复算承担（口径见器具声明）

## 候选⑤ 起手闸余量条款

- 余量源 = r595 同态在飞窗实测振幅 133MB；ceiling=2781 / margin=71 / REQ=2721 / cap=71 / cap_binding=True ⇒ 真机行使 rc=0

## 铁律 11 前置器

- rc：`executable_and_correct=False` / `acceptable_scoped=False`；blocked=5 条（前 3 条: ["w172/agentD-r3/g1 rc=1 cases=47/58(expect 58) failed=wythoff#43-public,wythoff#44-public,wythoff#45-hidden,wythoff#46-hidden,wythoff#47-hidden,wythoff#48-hidden,wythoff#49-hidden,wythoff#50-hidden,wythoff#55-hidden,wythoff#56-hidden,wythoff#57-hidden", "w173/agentD-r1/g1 rc=1 cases=55/58(expect 58) failed=wythoff#50-hidden,wythoff#55-hidden,wythoff#57-hidden", "w173/codex/g1 rc=1 cases=56/58(expect 58) failed=wythoff#43-public,wythoff#57-hidden"]）

## 诚实边界

- 铁律 11 rc≠0 ⇒ 全部质量/成本读数标「参考（未可验收）」，**不宣称任何降幅/增益**；
- 候选②③④ 为只读/聚合面 ⇒ 不构成能力验收、不得回写成「产品已修」；
- 跨轮/跨窗集**禁相减**，只并列；候选①（产品侧修复）**待用户放行**。
