# R419 对照观测：`correction=always`（假前提修正轮）

**这不是 PASS 证据，是一条被归档的负向观测**；本轮 KPI 判据只用 `correction=onfail` 批（见同级 `check-<NS>.out`）。

## 为什么归档
R419 首跑（批次后缀 `b09141437`）用旧实现：**对每题都发修正提示**，包括首轮已经整题全对的题。
于是提示里的前提「你的隐藏用例 #k 没过」对已过题为**假**。实测后果：

| 题 | 首轮(t1) | 修正轮后(t2) | 变化 |
|---|---|---|---|
| p002 | ok（整题全对） | partial（18 用例 15 过） | **回归** |
| p003 | ok（整题全对） | runtime_error（1/18 过） | **回归** |
| p001 | syntax_error | syntax_error | 未通过（无变化） |

读数：`first_try_rate_whole=0.6667` → `final_rate_whole=0.0`；`fix_rate=0.0`；**`regressed=2`**；轮数 6/6。
即：**给已对的题发「你错了」的提示，agent 会把对的改坏** —— 首轮 2/3 → 两轮后 0/3。

## 由此产生的实现修订（不是放宽判据）
1. `run_probe.py` 新增 `--correction {onfail,always}`（默认 `onfail`）：**只在首轮整题未过时才发修正轮** ⇒ 修正提示的前提恒为真，量到的才叫「修复率」。
2. 汇总新增 `regressed`（首轮过 ∧ 末轮不过）与 `correction_mode` 字段；`rounds_expected` 改为「实际发出的轮数」之和（onfail 下 ≠ `turns × 题数`）。
3. `check_multiturn.py` 判据 C 拆为 **C1 非回归（`final >= first`）/ C2 `regressed==0` / C3 增益与账本成对**，并断言 `correction_mode == onfail`；真机臂若首轮即全对（饱和）⇒ 如实标 `fix_rate=n/a`，不判失败。

## 证据清单（本目录）
- `probe-agent-seed419-r419bagent-b09141437-t2.json` — sha256 `45d01559ff06d8d2e045715bbb030690…`
- `agentr419bagent-b09141437-p{001,002,003}-t{1,2}.txt` — 6 份归档回复原文（判定器只读这些）

同批控制臂（`r419bctlpos`/`r419bctlneg`）与真机臂已在新实现下重跑，见 `../logs/`。
