# R569 轮志 · 剂量轴新窗集 (0 vs 3 × w137..w142) + 拒收窗定因 + 起手闸上界行使

> 形态：**零产品源码改动 / 零新增夹具 / 零新增开关**（用户令 2026-09-18「不许新增夹具和额外开发了」）。
> 唯一自由度 = 既有 env 开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` ∈ {0, 3}；全臂共用**同一枚** AOT 二进制
> （sha `320d0eb17e709d15`，runner 第 0 步机检）⇒ 臂身份由构造保证。题面/夹具/role/窗口逐字节同。

## 0. 候选台账（一轮全做，未做的写原因）

| 候选 | 内容 | 状态 | rc | 结论 |
|---|---|---|---|---|
| ① | 契约加厚 v3 / 产物落点自验 | **未做** | — | 须动契约或产品分支 ⇒ **待放行** |
| ② | 交付闸/停止条件（rc=5/rc=8 仍交付） | **未做** | — | 须新增产品分支 ⇒ **待放行**；本轮由 ④ 做只读定因 |
| ③（承重） | 剂量轴新窗集单变量 0 vs 3（6 新窗 × 3 臂） | 做 | 1 | **剂量档位非承重变量**（摆动 15 ≫ 效应 −1.5）⇒ 定案关闭 |
| ④ | 拒收窗（R568 记「臂级崩溃窗」）定因 | 做 | 0 | **不是崩溃，是自测闸拒收**（8/8 公开例失败 ⇒ rc=8，未宣称正确） |
| ⑤ | 起手闸 MARGIN 上界规则 + 条款行使 | 做 | 0 | 上界规则**当轮真行使**（attempt1 拒跑 → attempt2 放行）；postcheck rc=0 |

## 1. 判定与验收（判据 v2，未改判据）

- **判决 rc=1 · FAIL(被测/前提)**：配对面 `quality_paired_shortfall:R569B0,R569B3`
  （两臂相对同窗 codex 真值均短口：中位 −5.5 / −8.5，最短 −15）。
- **真值面**：codex 六窗**全部 58/58**（中位 58、极差 0），六窗状态全 `reliable`
  ⇒ 本轮真值侧无崩窗、无 `unreliable` 窗，配对合法。
- **铁律 11 前置器 rc=1**（`expected_stdout_exhausted` 等 9 条 `BLOCKED`）⇒ **本轮全部成本/降幅读数标「参考（未可验收）」**。
  诚实边界：`self_report_agrees=True`（产品自报与独立物化复跑一致）⇒ 无「自报通过而实测不过」的假绿。
- **指纹/口径恒等式 rc=0**：C4-1 恒等式 21/21 调用 0 违反；C4-2 确定性（行使臂每窗第 1 次调用 prompt sha8 唯一 `b9068f56`）；
  C4-3 非平凡（call1 ≠ call2 逐窗互异，5/5）⇒ 确定性**不是**恒定输出。

## 2. 剂量轴结果（承重候选 ③）

| 窗 | codex 真值 | B0(剂量0) | B3(剂量3) | Δ(B3−B0) | B0 成本 调用/新算 | B3 成本 调用/新算 |
|---|---|---|---|---|---|---|
| w137 | 58/58 | 52 | 53 | **+1** | 1 / 151 | 2 / 674 |
| w138 | 58/58 | 58 | 46 | **−12** | 1 / 151 | 4 / 1054 |
| w139 | 58/58 | 52 | 44 | **−8** | 1 / 151 | 4 / 690 |
| w140 | 58/58 | 43 | 43 | 0 | 1 / 151 | 4 / 1292 |
| w141 | 58/58 | 58 | 55 | **−3** | 1 / 151 | 6 / 2339 |
| w142 | 58/58 | 53 | 58 | **+5** | 1 / 151 | 1 / 151 |

- 配对数 n=6：**中位 −1.5**、极差 **[−12, +5]**；同臂跨窗摆动 **各 15**（B0 43–58、B3 43–58）。
- **摆动 ≫ 效应** ⇒ 按并池纪律（skill `kpi-eval-harness-design`：摆动 ≥ 效应 ⇒ 该轴非承重变量、**定案关闭**）：
  **剂量档位 (0 vs 3) 不是承重变量**。与预注册 `expected_direction` ① 一致（「无增益预期」）；预注册 ② 的
  「效应 > 摆动」前提**不成立** ⇒ 不单列增益候选、不作任何增益宣称。
- **代价面**：剂量 3 用 **3.5× 调用**（21 vs 6）、**6.8× 新算 prompt**（6,200 vs 906）、**2.9× completion**
  （45,687 vs 15,762），换 **中位 −1.5**（零增益）。R567 窗集上的「+4 平均增益」在本窗集**不复现**
  ⇒ 跨轮**禁相减**，只并列：该 +4 的候选地位被本轮否证。
- 修复轮面（剂量轴的真实作用点）：B3 `exec_repairs` 逐窗 [1,3,3,3,3,0]（中位 3），B0 全 0
  ⇒ 机制**确已启用**（非 `mechanism-not-engaged`），但启用后质量反而更低（w138/w139 逃逸到 `expect_stdout_exhausted`）。

## 3. 候选 ④：拒收窗定因（零开发只读，rc=0）

R568 把 `w104/R559B0` 记为「臂级崩溃窗」——**该定名错误**，三层判据（`cause_reject_window_r569.py`）：

| 层 | 读数 | 含义 |
|---|---|---|
| L1 落盘层 | 快照产物**存在**（`games/__main__.py` 227 B 等，逐件 sha 已录） | **不是崩溃**（无产物才叫崩溃） |
| L2 判定层 | 冻结判分器在**副本**上复跑：**0/58**，失败模式**唯一** `stdout_mismatch × 58` | 不是硬崩（无 rc≠0、无输出畸形） |
| L3 交付层 | 产品 transcript：`rc=8 · stage=public_probe_unmet · public_probe_reason=public_examples_failed · public_probe_total=8 · failed=8 · self_test_unmet=1 · correctness_asserted=0 · calls=1 · steps 6/6 · repair_rounds=0` | **自测闸（8 条公开例全败）⇒ 产品拒收交付并如实不宣称正确** |

**同类普查**（跨轮全臂窗，机取）：`rc=8` 共 10 个臂窗，其中 `stage=public_probe_unmet` 的有
`R559/w104/R559B0` **与 R569 本轮的 `w140/R569B3`** ⇒ 该类**在本轮天然复现**，不是一次性事故。
判据价值：把「拒收（闸未过 ⇒ 不交付）」与「崩溃（产物缺失）」分开，否则会把**诚实的失败**读成**能力或稳定性缺陷**，
并据此去修错东西。

## 4. 候选 ⑤：起手闸 MARGIN 上界规则当轮真行使

| 项 | attempt1 | attempt2 |
|---|---|---|
| 观测振幅 | — | 90 MB（`run-samples.jsonl` 182 采样，drift=false） |
| ceiling / REQ | 2640 / 2753 ⇒ **拒跑** | 2803 / 2753 ⇒ 放行 |
| margin | — | want 103 / cap 153，`margin_capped=false` |
| 产物 | `gate-margin-r569-attempt1-blocked.json`（**保留**，未覆盖） | `gate-margin-r569.json`（rc=0）+ `gate-postcheck-r569.json`（rc=0） |

attempt1 的拒跑是**真实拒跑**：ceiling 被 `pyright-langserver`（≈250 MB，由本轮 .py 写入拉起）压低
⇒ 按纪律回收 LSP 后 `MemAvailable` 2692→2878 MB，attempt2 放行。**上界规则（cap）未被行使**（`margin_capped=false`）
已如实登记，不得宣称行使。

## 5. 本轮自捕：器具**使用**缺陷（非产品、非被测）

- `matrix_r569.py` 的 `--work` 是**会被 `shutil.rmtree` 清空的输出目录**（默认 `/tmp/r569/pc` 即 scratch）。
  本轮误传 `--work /tmp/r569`（运行根）⇒ 清掉运行根日志面 `logs/`（run.txt、windows.jsonl、samples）、
  `adapter/`、`agent-cfg/`、`gate-*.json`。
- **结论面不依赖被清件**：全部读数在 06:08 前已由 ingest/kpi 落入**仓内**（`kpi-table-r569.json`、
  `fingerprint-r569.json`、`adjudication-r569.json`、`evidence/windows/*/report.json`、
  `eval/rover/r507pre/precondition-r569.json`），或由**冻结快照**重算（`matrix-r569.json`）。本件即重算凭据。
- 补做：`closeout_r569.py` 由仓内冻结件重算 **`windows-r569.json` / `verdict-r569.json` / `summary-r569.json`**
  （post-hoc，已在件内标注来源），并对两条独立路径（`evidence/windows/*/report.json` vs `kpi-table`）做逐窗交叉校验：
  **18/18 一致，0 不符**。
- 代价（诚实边界）：**plan 步数面（`steps_executed`/`plan_steps_total`）本轮丢失** ⇒ 表内记「未测」；
  修复轮面（`exec_repairs`）保留。教训（已在协议层）：器具的 `--work` 一律指向 scratch，禁指运行根。

## 6. 落盘件

`prereg-r569.json`（先写后跑）、`bins-r569.json`（臂身份/二进制 sha/env 定义）、`gate-margin-r569.json`
+ `-attempt1-blocked.json`、`gate-postcheck-r569.json`、`fingerprint-r569.json`、`kpi-table-r569.json`、
`matrix-r569.py` + `matrix-r569.json`、`adjudicate_r569.py` + `adjudication-r569.json`、
`cause_reject_window_r569.py` + `readings-candidate4-r569.json` + `evidence/transcripts/transcript-w104-R559B0.json`、
`closeout_r569.py` + `windows-r569.json` / `verdict-r569.json` / `summary-r569.json`、
`eval/rover/r507pre/precondition-r569.json`。

## 7. 下一轮候选（供下轮预注册）

1. **③′ 剂量轴第三窗集**——除非换窗集能给出「效应 > 摆动」，否则**不再开**（本轴已判非承重、关闭；重开条件 = 换承重面或臂内机制改动）。
2. **② 交付闸语义**（待放行才动）：`rc=8` 已证明产品**会**拒收；缺的是「拒收后是否给出可见原因/是否有界重试」——先只读取证，不新增分支。
3. **① 契约加厚 v3**（待放行）：g1 族 wythoff 失分三次定因为**产物缺陷**，属契约/自验面，须用户放行。
4. **步数面补读**：任何后续轮都要在**仓内**留 step 面（transcript 落仓内或 ingest 吸收 `steps_executed`），防同类丢失。
