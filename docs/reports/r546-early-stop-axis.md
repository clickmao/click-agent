# R546 — g1 长任务的**早停轴**单变量对照(探针已判不合格 ⇒ 省掉那次回灌修复请求)

> 窗口 w1 · 臂 13 个/窗 · 题面 `g1`(58 隐藏用例, sha256 `ed13dd23577db893` 与 R544/R545 逐字节同) · AOT `1224d3f4ec61d267` 15,812,016 B (IL 警告 0)

## 0 靶点与单变量

- **靶点来源**: R545 下轮候选 ①(用户 R413 判据的直接抓手)。R545 事后单列已证「公开面失败数 pfail ∈ {0,2,4} ⇒ 隐藏用例均值 58.0/45.0/33.0 单调降」⇒ pfail 有预测力; **但那次「回灌修复」远端调用的边际价值从未被单变量检验**。
- **单变量** = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {unset(=0 轴关), 2(轴开)}`: 轴开 ⇒ 探针回放已判 pfail ≥ 2 时**不再**花一次远端调用做回灌修复(执行证据回灌同样终止 —— 这是轴的定义), 直接走既有终端分类(**rc 语义不变**)。
- 其余全同: 题面/用例/role/二进制/`MAX_EXEC_REPAIR=1`/探针开关(`PUBLIC_SELFCHECK=1`, **两列都开**) ⇒ 起臂前逐字节机检(cases md5 / role md5 / prompt sha256 与 R545 相同)。

## 1 产品改动(代码事实)

| 文件 | 改动 | 关闭态安全性 |
|---|---|---|
| `src/agent/r1/R1Options.cs` | 新增第 9 位可选参数 `EarlyStopPfail=0` + env 解析(`0..10`, 非法 ⇒ 0) | 默认 0 ⇒ 无行为差 |
| `src/agent/r1/R1Pipeline.cs` | 探针失败分支: `earlyStop = opt.EarlyStopPfail>0 && probe.Failed>=opt.EarlyStopPfail`; 命中 ⇒ 记录 `R1_EARLY_STOP{...}` 标记 + 跳过修复 + 终端条件加 `|| earlyStopSkips>0`(堵住「早停后又走执行修复」的漏) | 0 ⇒ `earlyStop=false` ⇒ 逐位旧路径 |
| `src/agent/r1/R1RunResult.cs` | 新增 `EarlyStopThreshold` / `EarlyStopSkipped`(可选参数) | 0 ⇒ 字段不出现 |
| `src/agent/r1/R1Transcript.cs` | 台账/Marker 仅在 `EarlyStopThreshold>0` 时输出 `early_stop_pfail`/`early_stop_skipped` | 轴关臂台账与旧版**逐字节同**(J12 机检「字段缺席」) |

## 2 器具与硬门

- `eval/rover/r546/`: `setup_r546.py`(夹具逐字节复制 + md5 交叉核对 + 预注册生成) → `port_r546.py`(从 R545 派生 runner/读数器, **逐处替换断言命中**) → `run_r546.sh` → `analyze_r546.py`。
- 硬门: 起手闸 2×PASS · 输入钉逐项机检 · 预注册范围闸 `prereg_scope_gate.py` rc=0 · 冒烟(`hello=yes`) · 每臂 `adapter_range` 非空(实发用量可核)。
- 读数三路交叉: 台账(机制) / adapter 中继 usage(付费口径) / 58 隐藏用例独立进程真跑(**唯一正确性证据**)。

## 3 同窗读数

| 臂 | 轴 | rc | 调用 | prompt | compl | total | 隐藏用例 | pfail | 早停跳过 | exec_repairs |
|---|---|---|---|---|---|---|---|---|---|---|
| w1/E0a | 关(0) | 4 | 2 | 16,237 | 2,507 | 18,744 | 0/58 | None | None | 0 |
| w1/E0b | 关(0) | 0 | 1 | 8,083 | 2,441 | 10,524 | 56/58 | 0 | None | 0 |
| w1/E0c | 关(0) | 5 | 4 | 32,767 | 5,852 | 38,619 | 58/58 | 0 | None | 1 |
| w1/E0d | 关(0) | 8 | 2 | 16,548 | 3,966 | 20,514 | 58/58 | 0 | None | 1 |
| w1/E0e | 关(0) | 8 | 2 | 16,308 | 4,249 | 20,557 | 50/58 | 1 | None | 1 |
| w1/E1a | 开(pfail≥2) | 0 | 2 | 16,308 | 4,285 | 20,593 | 58/58 | 0 | 0 | 1 |
| w1/E1b | 开(pfail≥2) | 5 | 1 | 8,083 | 1,912 | 9,995 | 43/58 | 2 | 1 | 0 |
| w1/E1c | 开(pfail≥2) | 8 | 2 | 16,547 | 3,729 | 20,276 | 44/58 | 2 | 1 | 1 |
| w1/E1d | 开(pfail≥2) | 5 | 4 | 32,859 | 8,220 | 41,079 | 58/58 | 0 | 0 | 1 |
| w1/E1e | 开(pfail≥2) | 0 | 2 | 16,308 | 5,127 | 21,435 | 58/58 | 0 | 0 | 1 |
| w1/A1on | 旧路径 | None | 12 | 151,561 | 13,320 | 164,881 | 58/58 | None | None | None |
| w1/A1onb | 旧路径 | None | 9 | 90,525 | 7,316 | 97,841 | 58/58 | None | None | None |
| w1/A1onc | 旧路径 | None | 4 | 33,036 | 4,593 | 37,629 | 56/58 | None | None | None |

- **off**(n=5): 用例 [0, 56, 58, 58, 50](中位 56, 全绿 2/5) · 调用 [2, 1, 4, 2, 2](中位 2) · total 中位 20,514 · rc [4, 0, 5, 8, 8] · 假成功 1
- **on**(n=5): 用例 [58, 43, 44, 58, 58](中位 58, 全绿 3/5) · 调用 [2, 1, 2, 4, 2](中位 2) · total 中位 20,593 · rc [0, 5, 8, 5, 0] · 假成功 0
- **legacy**(n=3): 用例 [58, 58, 56](中位 58, 全绿 2/3) · 调用 [12, 9, 4](中位 9) · total 中位 97,841 · rc [None, None, None] · 假成功 0

## 4 判据(本轮预注册 = J10/J11/J12)

- **J10 机制(轴真生效)**: `机制未被行使(某类样本为空, 禁宣称省调用)` —— 轴开臂 pfail≥2 的臂 {"E1b": {"pfail": 2, "skipped": 1, "exec_repairs": 0, "calls": 1, "reply_marker": true}, "E1c": {"pfail": 2, "skipped": 1, "exec_repairs": 1, "calls": 2, "reply_marker": true}} ⇒ 全部 `early_stop_skipped=1` ∧ reply 含 `R1_EARLY_STOP`; 同窗轴关同 pfail 臂 {} ⇒ **反事实类为空** ⇒ 预注册的「同终态 pfail 配对」在本窗不可构造(轴关列被修复回 pfail≤1) ⇒ 省调用宣称收窄为「器具级成对单测 + 行使臂实测」, 见 §4b
- **J11 代价(配对)**: pfail≥2 子集调用 off None → on 1.5(合计 0 → 3, **省 None 次**); 全臂调用中位 2 → 2; **判别性阴性对照** pfail<2 子集 off [1, 2, 2, 2, 4] / on [2, 2, 4]。**轴关列同终态 pfail≥2 臂 = 空 ⇒ 上表该子集不可比, 省调用数一律标「参考(未可验收)」**
- **J12 零回归(字段缺席 + 单测成对)**: `PASS` —— 轴关臂 `early_stop_*` 字段值 [None, None, None, None, None](应全 None) ⇒ 台账与旧版同; 轴开臂阈值全 = 2 = True。器具级成对单测 `src/agent.tests/R1EarlyStopTests.cs` 4/4: **同输入轴关 `Calls=2`(修复真发生) / 轴开 `Calls=1`(省掉那次) / 阈值 5 不触发(负控)**。
- 携带读数(非本轮变量, 只作对照): J1v2 `{"scope": "on 臂中**产物在盘**(work 文件数>0, 非自报)的臂 ⇒ 必须 public_probe_ran=1", "reachable_on_arms": ["E1a", "E1b", "E1c", "E1d", "E1e"], "on_ran": [1, 1, 1, 1, 1], "on_a` · J8 `{"trigger_rc_set_on": [0, 5], "nonzero_exit_covered": true, "note": "v1 的触发面只有 rc=0 ⇒ 该集合必为 {0}; v2 若出现 ≠0 值 ⇒ 旧触发面外的出口真被覆盖"}` · J3 `{"off_all_green": [false, false, true, true, false], "on_all_green": [true, false, false, true, true], "off_cases": [0, 56, 58, 58, 50], "on_cases": [58, 43, 44` · J4 `{"calls": {"off_median": 2, "on_median": 2, "ratio_on_off": 1.0}, "prompt": {"off_median": 16308, "on_median": 16308, "ratio_on_off": 1.0}, "completion": {"off_median": 3966, "on_median": 4285, "ratio_on_off": 1.08}, "to`

## 4b post-hoc(非预注册, 单列: 预注册 J10 的配对类在本窗为空 ⇒ 宣称收窄)

```json
{
 "name": "J10 反事实缺口的收窄读数(非预注册)",
 "why": "预注册 J10 要求「轴关列存在同**终态** pfail≥2 臂」作配对反事实; 本窗轴关列 5/5 臂终态 pfail ≤ 1(修复把公开面修回去了) ⇒ 该配对类为空, 预注册的省调用宣称在本窗**不可直接验收**(收窄, 不作废判据本身)。",
 "fired_arms_on": {
  "E1b": {
   "pfail": 2,
   "calls": 1,
   "exec_repairs": 0,
   "marker": true
  },
  "E1c": {
   "pfail": 2,
   "calls": 2,
   "exec_repairs": 1,
   "marker": true
  }
 },
 "off_repaired_arms": {
  "w1/E0c": {
   "exec_repairs": 1,
   "calls": 4,
   "pfail_final": 0,
   "cases": 58
  },
  "w1/E0d": {
   "exec_repairs": 1,
   "calls": 2,
   "pfail_final": 0,
   "cases": 58
  },
  "w1/E0e": {
   "exec_repairs": 1,
   "calls": 2,
   "pfail_final": 1,
   "cases": 50
  }
 },
 "off_repaired_calls_dist": [
  2,
  2,
  4
 ],
 "unit_level_pin": "器具级成对单测 `R1EarlyStopTests`: **同一脚本输入** 轴关 `Calls=2`(修复真发生) → 轴开 `Calls=1`(省掉那次) ⇒ 「早停省 1 次远端调用」在单元面是机械成对证据; 窗内只报「行使臂实测调用数 vs 轴关列分布」, 标参考。",
 "posthoc_side_effect": "轴关列被修复回 pfail≤1 而同列隐藏用例 [50, 58, 58]; 轴开行使臂终态 pfail=2, 隐藏用例 [43, 44]—— 方向与「修复有效」一致但样本 n=3/2, **不足以下结论**(预注册未声明质量非劣的配对检验)。"
}
```

## 5 铁律 11 前置器

- `python3 eval/rover/r507pre/exec_precondition.py --round r546` ⇒ **rc=1 (未可验收(BLOCKED 逐条点名))**
- 阻塞臂(6): w1/agentA1onc-g1, w1/agentE0a-g1, w1/agentE0b-g1, w1/agentE0e-g1, w1/agentE1b-g1, w1/agentE1c-g1

## 6 复现

```bash
python3 eval/rover/r546/setup_r546.py && python3 eval/rover/r546/port_r546.py
bash eval/rover/r546/run_r546.sh w1     # w2 同
python3 eval/rover/r507pre/exec_precondition.py --round r546
```
