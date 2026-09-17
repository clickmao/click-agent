# R512 · 外部真值对照 (p3+p4 两侧 n=2) + 预注册增补臂 B — p4 夹具缺陷定位

## 0 结论 (一段)
R512 按主线定义跑「同环境·同输入·同模型」外部真值对照 (本侧 agent vs codex-cli, 同一真实模型 deepseek-chat): 题集 = p3 (线程化 KV 服务) + p4 (任务队列 CLI), 两臂各 n=2, 另按**预注册增补**(起臂前落盘 `prereg-r512-addendum.json`)加 B 臂 (预算 12) n=2。机检判据 C1/C2/C3/C4 全过 (C3 token 比 max=0.6165 ≤ 0.70; C4 调用比 max=0.5714 ≤ 1.00), 但 **C5 (铁律 11 可执行且正确) 未过 ⇒ 本轮 token/调用降幅一律标「参考 (未可验收)」**。失败根源经机检定位为 **p4 题面缺陷**: 题面第 2 条只写「全局选项 `--now` 注入当前时间」而**未写缺省语义**, 隐藏用例 12 条中 8 条不带 `--now` 调用 ⇒ 判据依赖题面未写明的约定; p4 上三个臂 (agentA/agentB/codex) 的失败用例集合**逐字相同** (4/12), 即**外部真值同样失败** ⇒ 该失败不构成本侧质量缺陷证据, 而是夹具与题面口径不一致 ⇒ 判据丧失区分力。p3 子集两侧全部 12/12, 该子集上调用 ↓87–91%、token ↓89–95% (仅供参考, 因 C5 未过)。

## 1 本轮产出 (文件 / 命令 / 读数)
| 产物 | 路径 | 关键读数 |
|---|---|---|
| 题集 (取 R511 题面逐字节, 补全 project 字段) | `eval/rover/r512/taskset-r512.json` | 题面 sha 与 R511 逐题相等 (机检) |
| 预注册 (机检, 起臂前) | `eval/rover/r512/prereg-r512.json` | 15 项器具哈希 + 5 判据 + 验收面 `['*/agentA','*/codex']` |
| 预注册增补 (B 臂, B 起臂前) | `eval/rover/r512/prereg-r512-addendum.json` | B 臂 = 预算 12; 记中止尝试台账 |
| 跑器 | `eval/rover/r512/run_contrast_r512.sh` | 起手闸 2×PASS; 端口 48690; teardown 端口已释放 |
| 判据机检 | `eval/rover/r512/check_criteria_r512.py` → `evidence/checks-r512.json` | C1/C2/C3/C4 PASS, C5 FAIL |
| 判据器负控 | `eval/rover/r512/nc_r512.py` → `evidence/nc-r512.json` | `SELFTEST=OK` (正控 p3/p4 各 12/12; 6 变异体全检出) |
| 快照 (不可变) | `eval/rover/r512/snapshots/w{1,2}/{agentA,agentB,codex}/` | 23 + 22 件 |
| 窗口证据 | `eval/rover/r512/evidence/windows/w{1,2}/report.json` | 每窗 6 臂-题 |
| 铁律 11 前置 | `python3 eval/rover/r507pre/exec_precondition.py --round R512` | **rc=1** `ACCEPTABLE_SCOPED=False` `SELF_REPORT_AGREES=True` |
| 排除台账 | `eval/rover/r512/evidence/excluded-dumps-r512.json` | agent 侧 dump 29–58 (30 个) = 中止尝试, 不计入任何臂 |

## 2 读数 (adapter 落盘 usage 真值 + 隐藏用例机判; 逐位见 `evidence/summary-r512.txt`)
| 跑次 | 题 | 用例 | 全对 | 调用 | tokens | 秒 |
|---|---|---|---|---|---|---|
| A-r1 (agent 默认) | p3 | 12/12 | ✓ | 7 | 119,530 | 48.6 |
| A-r1 | p4 | 2/12 | ✗ | 7 | 76,109 | 28.2 |
| A-r2 | p3 | 12/12 | ✓ | 7 | 94,607 | 35.9 |
| A-r2 | p4 | 4/12 | ✗ | 7 | 85,302 | 31.7 |
| B-r1 (agent 12 步) | p3 | 12/12 | ✓ | 4 | 60,449 | 28.4 |
| B-r1 | p4 | 4/12 | ✗ | 9 | 126,086 | 40.7 |
| B-r2 | p3 | 12/12 | ✓ | 14 | 263,437 | 61.0 |
| B-r2 | p4 | 4/12 | ✗ | 8 | 87,164 | 24.3 |
| C-r1 (codex 真值) | p3 | 12/12 | ✓ | 46 | 1,266,833 | 174.7 |
| C-r1 | p4 | 4/12 | ✗ | 16 | 204,505 | 50.3 |
| C-r2 | p3 | 12/12 | ✓ | 43 | 849,925 | 87.6 |
| C-r2 | p4 | 4/12 | ✗ | 14 | 192,019 | 67.3 |

- 窗口配对比 (agent/codex): p3 token 0.0477 / 0.31; p4 0.6165 / 0.4539; 调用比 p3 0.087 / 0.3256; p4 0.5625 / 0.5714。
- 三臂 p4 失败集合逐字相同: `add_creates_and_lists, id_monotonic_no_reuse, unicode_roundtrip, done_idempotent, done_unknown_id, persistence_across_processes, no_temp_residue, list_filter_and_order` (A-r1 额外多 `ttl_expiry_uses_injected_clock, expire_removes_expired_tasks`)。

## 3 缺陷定位 (可重放)
1. `eval/rover/r511/cases/p4_cases.py:63` `cli("--db", db, "add", "买菜")` — **不带** `--now`。
2. 复现 (codex 侧产物): `cd /tmp/r512/run-0917-095853/C-r1/p4/work && python3 -B -m tasksvc.cli --db /tmp/t1.json add 买菜` → `{"error":"bad_request"}` rc=2; 加 `--now 1000` → rc=0 正常。
3. 产物自述: 该实现 `cli.py:103` `if now is None: raise BadRequest("--now is required")` ⇒ 把题面未写明的缺省判为必填。
4. 题面 (v1, sha `678624f5…`) 第 2 条全文: 「时钟：全局选项 `--now <epoch 秒>` 注入当前时间（浮点或整数）。所有时间判定只准用该时钟，禁止 sleep。」——无缺省语句。
⇒ 判据 = 由参考解**隐式**定义的约定, 未回写题面。**修法见 R513 (题面 v2, 用例与参考解逐字节不变)**。
**旁证 (非本轮新引入)**: R511 入册行的 `negative_control` 已写「忽略 `--now` ⇒ 11/12 红」——即 R511 的负控已见过该脆弱约定, 但当时未把它当夹具缺陷处理 ⇒ 本轮把它从「p4 分数低」升级为「判据-题面不一致」并机检定位。

## 4 诚实边界
- **未可验收**: C5 FAIL (rc=1) ⇒ 上述 token/调用降幅只是「参考」, 不作为验收依据。
- 增补臂 B 相对主预注册属**事后增补** (虽在 B 起臂前落盘): 其读数不作主验收依据; 且 B 臂与 C 臂同属一次跑器执行体、时序相邻 (R508 同惯例), 非独立重复实验。
- B 臂曾有 3 次中止/作废尝试 (含一次与并发跑次交错), 已按 `adapter_range` 显式排除区段 29–58 (30 个 dump); 该区段内读数无归属, 未计入任何臂。
- 判据器首次负控报 `NC_NOT_DETECTED` 系**我方预期名写错** (用例名不带 `test_` 前缀), 非判分器缺陷; 修正后 `SELFTEST=OK`。
- 未测: p1/p2/p5 任务; codex 侧预算曲线; 外部真值除 codex-cli 外的第二参照 (未测到的就是没测到)。
- 清理: 本轮 nc 首跑把 `_grade.json` 落在参考解树内 (r508/ref/p3、r511/ref/p4 各 1406/1292 B), 已删除并改为「只对副本判分」; 删除物已记 (bytes,sha256) 于本节。其中 `eval/rover/r508/ref/p3/_grade.json` 系 **R508 已入库件** ⇒ 已 `git checkout` 还原 (该树仍与 R512 预注册哈希一致, 已机检 15 项器具/题面 0 漂移, 唯一例外见下)。
- **器具预注册后修订 1 处 (已声明)**: `freeze_snapshot_r512.py` 在预注册后新增 `--append` (为把增补臂 B 追加进既有窗口 w1/w2), sha12 `c777ae37650b` → `f68a08aa8159`; 只影响快照入库动作, 判分/用量器具未动 ⇒ 读数口径不变。台账: `eval/rover/r512/evidence/instrument-drift-r512.json` (R513 复制件继承同语义)。

## 5 下轮候选
1. **R513 (本 tick 已执行)**: p4 题面 v2 (写明 `--now` 缺省 = 系统时钟) + 两侧 n=2 重测 ⇒ 争取 C5 rc=0 的**可验收**读数。
2. p4 隐藏用例的「题面依据」逐条审计 (本轮只定位到 1 处; 其余约定是否也由参考解隐式定义, 未穷举)。
3. p1/p2/p5 任务纳入对照 (题集面扩宽)。
4. B 臂预算曲线 (6/9/12/16 × n≥3) 定量化; 本轮只测了 6 与 12 两点。
