# R499 · 本地改写通道真机取证 —— 判据器/派生器先行 + 起手闸让行

状态: 部分完成（判据面与器具面已交付并自检；**真机 4 臂让行未跑**，窗口被对侧会话占满）
轮号: R499（主线轮；R413：r1 真假判别 ⇒ 一轮任务 token 下降 ≥30%）
日期: 2026-09-17 01:2x–02:3x (+0800)
被测产物: `/tmp/pub_r499/agenthost`（AOT，IL 警告 0，15,409,088 B，sha256 `3a79bbb4cfbec807…`，smoke rc=0）
预注册: `eval/rover/r499/prereg_r499.json`（**先于首跑落盘**）

## 1 因果链

R497 候选④b「『换个说法/讲细一点』不吸收」的机理 = 本地消化面只有**模板 ack** 与**原样回放**两条零生成通道，
同义改写族若按这两条吸收就会退化成回放/模板（R488 退化族）⇒ R498 补第三条通道「用 r1 对上一条实质答复改写」
（`LocalParaphraseChannel`，闸 `AGENTFRAMEWORK_LOCAL_PARAPHRASE` 默认关，只有字面 `"1"` 算开）。
R498 只做了**离线**取证（守卫不变量 + 单测），真机单变量从未跑过 ⇒ R499 的靶点 = 同窗 C（闸关）/ P×3（闸开）
单变量真机取证 + 质量面 n≥3。

执行到起手闸即被拦：**对侧会话正在本仓连续构建**（`src/agent.rag/**/bin|obj` 每 3 分钟有新写入、
`VBCSCompiler` 长驻、`recent_src_writes_120s` 480/92/37/258 次），`MemAvailable` 在阈值 2650 MB 两侧反复穿越
（六次采样：2208 / 2315 / 2528 / 2544 / 2592 / **2654**）⇒ 按 R486/R495 纪律**让行**，本轮不起真机测量。

## 2 产出表（逐项：做/未做 + 证据）

| # | 项 | 状态 | 证据 |
|---|---|---|---|
| ① | 臂执行器机派生（r497→r499，唯一改动入口，带 aux 同批携带 + 失败不写盘） | **做** | `eval/rover/r499/build_r499_harness.py`（136 行）→ `run_arm_real_r499.sh`（`bash -n` 通过；N1..N5 断言全过） |
| ② | 臂矩阵（C 关 ×1 + P 开 ×3，非零 rc 即中止）+ 网格逐字节继承 | **做** | `run_rest_r499.sh`；`cmp` 与 `eval/rover/r497/grid/task-p17-code.json` 逐字节同 |
| ③ | AOT 重发布 + IL/特征检查 | **做** | `publish_and_il_check_r499.sh` + `binary-check-r499.txt`：PUBLISH_RC=0 / IL 警告 0 / CLASS_MISSING=(none) / SMOKE_RC=0 |
| ④ | 判据器（门态正控 + 改写质量结构不变量 + 成本面 + 族回归 + fail-closed） | **做** | `judge_paraphrase_r499.py`；干跑 R497/T1 ⇒ `VERDICT=GREEN red=0`（`judge-selftest-r499.txt`） |
| ⑤ | 判据器负控（三态注入） | **部分** | `nc_c_absorb` 实测 `rc=1 red=1`；`nc_drop_gate_row` / `nc_template_reply` **待真机 P 臂落盘后补跑** |
| ⑥ | 汇总器（逐臂判据 + 同窗 C vs P×3 + n≥3 离散度 + 缺臂即让行） | **做** | `analyze_r499.py`（缺臂时输出 `arms_missing=[C,P1,P2,P3]` 并 rc=3，不冒充绿） |
| ⑦ | AOT 特征存在性**方法更正** | **做** | `probe_aot_string_presence.py` + `aot-string-presence-r499.txt` |
| ⑧ | 起手闸让行取证（六次采样 + O5 归属失真） | **做** | `make_evidence_r499.sh` + `gate-hold-r499.txt` |
| ⑨ | 登记表 3 行（含 bind_evidence 派生 + 并发守卫） | **做** | `register_r499.py`（foreign 207 行写前写后指纹不变）+ `R2E_R2F_EXIT=0` |
| ⑩ | **真机 4 臂（C/P1/P2/P3）** | **未做（让行）** | 起手闸内存红 5/6 次；命令已备：`bash eval/rover/r499/gate_retry_r499.sh && bash eval/rover/r499/run_rest_r499.sh` |

## 3 让行读数（同器具、同会话，六次采样）

| # | verdict | MemAvailable MB | cause | src 写入/120s | 备注 |
|---|---|---|---|---|---|
| 1 | GATE_BLOCKED | 2315 | 内存不足 + build-server 残留 | 480 | `refused[0]` 含 `O5_本轮驱动器在世`，驱动器实为**对侧** |
| 2 | GATE_BLOCKED | 2544 | 内存不足 | 0 | — |
| 3 | GATE_BLOCKED | 2528 | 内存不足 | 0 | — |
| 4 | **PASS** | **2654** | — | 92 | 同一次 `refused[]` **仍含 O5 判词** ⇒ 判词与判定自相矛盾 |
| 5 | GATE_BLOCKED | 2208 | 内存不足 + build-server 残留 | 258 | — |
| 6 | GATE_BLOCKED | 2592 | 内存不足 | 37 | — |

阈值 `MemAvailable ≥ 2650 MB`。六次中仅一次通过，且该次与 `O5` 判词并存 ⇒ 单次采样判定不可信。

**自伤一并登记**：`gate_retry_r499.sh` 首版只匹配 `GATE_PASS*`，而器具实际返回 `PASS` ⇒ 第 4 次已通过却被脚本判成未过（已修：`GATE_PASS*|PASS*`）。修法未回填那次读数，故上表照实并列。

## 4 判据器读数（干跑 + 负控）

- 干跑（`--dir eval/rover/r497 --arm T1 --mode C`）：`J1a/J1b/J1c` 全 OK、`J4t2..t5` 全 OK、`VERDICT=GREEN red=0`。
  注：J4 首版把 basis 白名单写死成 `ack|repeat|paraphrase`，而 R497 的载体是 `gate:skip→local` ⇒ 4 条**假红**；
  已改为「必须本地消化（0 远端调用）+ basis 非空」，**不是**放宽判据，而是口径纠正（载体属实现细节，不变量是「无远端调用」）。
- 负控 `nc_c_absorb`（把 C 臂第 8 条门行 basis 改成 `mechanical:paraphrase`）：`rc=1 red=1` ⇒ 注入被抓。

## 5 方法更正：AOT 产物「特征存在性」不能靠字符串 grep

| 钥匙 | `/tmp/pub_r498` ascii / utf16le | `/tmp/pub_r499` ascii / utf16le |
|---|---|---|
| `AGENTFRAMEWORK_LOCAL_PARAPHRASE` | 0 / 0 | 0 / 0 |
| `AGENTFRAMEWORK_REPLAY_PAIR_TRIM` | 0 / 0 | 0 / 0 |
| `AGENTFRAMEWORK_TOOL_DECL_GATE` | 0 / 0 | 0 / 0 |
| …（8 把钥匙全 0） | | |

同一产物上**元数据类型/方法名表**：`LocalParaphraseChannel` / `ReplayPairTrim` / `ToolDeclGate` /
`LocalDecisionLedger` / `MicroStepIsolationGate` / `LocalGenerationPort` / `ActionLoop` / `IndustrialAgentV2` = **8/8 命中**。
⇒ `grep -ac AGENTFRAMEWORK_X <bin>` 是**假阴性源**，发布检查已改为类名表（`CLASS_MISSING` 为空才放行）。
**连带更正**：R492「`/tmp/pub_r491/agenthost` 缺剪裁闸」的**方法面**不成立（该 grep 结论不可复现为证据）；
其**行为面**证据（闸置 on 后遥测 `pair_gate` 恒 `0`、`trimmed_sum=0`）独立保留。

## 6 诚实边界

1. **本轮无任何 KPI 读数**：真机 0 臂 ⇒ 不宣称改写通道的 token/质量增益；`prereg_r499.json` 的 H1–H4 全部**未测**（不是「通过」，也不是「失败」）。
2. 三态负控只跑了 1/3（另两态依赖 P 臂产物）；未跑前不得据负控宣称判据完备。
3. 起手闸 O5 归属失真的**修法未实施**（候选：驱动器用会话标识而非祖先 pid 集合；内存判据改「连续 3 次 ≥ 阈值」）。
4. 判据器的「新增标识符」检查是**结构不变量**，不证语义等价；语义正确性只能由真机人工细读取证（本轮未做）。
5. 被测二进制与对侧会话同源（同一 HEAD 发布），但发布时刻的 `obj/` 生成物可能被并发构建触碰 ⇒ `sha16` 已锁，跨轮不复用。

## 7 下轮候选

1. **窗口一开就跑 4 臂**：`bash eval/rover/r499/gate_retry_r499.sh && bash eval/rover/r499/run_rest_r499.sh && python3 eval/rover/r499/analyze_r499.py`（产出 `calls/usage/turns/tel/flags/teardown` + 逐臂判据 + n≥3 离散度）。
2. 补齐另两态负控（`nc_drop_gate_row` / `nc_template_reply`）。
3. 起手闸 O5 归属与会话标识修法 + 内存置信面（连续采样）。
4. 真机跑通后按 `prereg_r499.json` 逐条裁决 H1–H4，并把「改写族吸收」的收益与 R498 的挂载成本腿分列（禁混算）。
5. master plan 轮索引补 R491–R499（器具 `eval/tools/master_plan_round_index.py` 机取，不手改）。
6. EXP1 能力自检线（对侧会话线）不越界。
