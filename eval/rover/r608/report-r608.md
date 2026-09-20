# R608 轮工件 · RF0004.1 开工：开放域识别统一出口 `{标签|abstain, 依据}` 落地

日期 2026-09-21 · cron 60min tick · HEAD `82e8ab4ed72a942977932e9013391b0200921a9c`(起臂时) · 单变量 `AGENTFRAMEWORK_RECOGNITION_VERDICT`
DAG `eval/rover/r608/dag-r608.md` · 预注册 `eval/rover/r608/prereg-r608.json` · 判决 `eval/rover/r608/verdict-r608.json`(+negctl)

## 0 结论

- **verdict = FAIL / rc=1**，唯一红项 = `P2_ablation_bitwise_equivalent`（**预注册原样判，不翻案**）。
- 出口**落地面**：`P1_treatment_positive` PASS（T×3 事件 2/2/2）· `P2_control_zero` PASS（C×3 全 0）· `P3_outlet_coverage` PASS（覆盖 == 轮数 2）· `P4_frozen_prefix` PASS（前缀 15291 未破）· `P5_instrument_has_teeth` PASS（有牙）。
- **机制面 PASS**（出口发射可区分治疗/对照、覆盖全轮、AOT 产物下同样发射）；**能力面未测**（无质量对照臂）。
- 负控：`judge_r608.py --negctl`（交换 T/C 读数）⇒ `P1/P2/P3` 同时翻红 ⇒ 判据器**有牙**（rc=1）。
- 跳步（各一行原因）：**codex 质量对照臂**（出口落地轮无质量对照项，协议 §2 允许零质量面）· **恒前缀命中率**（REPL 面不产该口径，无中继 dump）。

## 1 DAG 与执行面（起手先出，见 `dag-r608.md`）

`N0 起手闸(环境) → N1 主线提醒 → N2 选靶(逐例归因=R607 盘点缺口三条) → N3 文献小步 → N4 预注册 → N5 产品侧最小改动 → N6 构建/AOT → N7 真机跑 → N8 判决 → N9 收口`
并行面：N3 与 N4 无依赖边但 N4 写同仓 ⇒ **未开子 agent**（同仓写者存在时并行节点限只读，本轮无只读需求）。

## 2 预注册与单变量（先写后跑闸）

- 先写后跑闸由 `run_r608.sh` 第 0 步机检：`round=R608 ∧ written_before_run=true ∧ arms={T,C} ∧ C==off ∧ T 不含该键 ∧ reps=3/3 ∧ criteria=5 ∧ falsification=3`（打印 `[先写后跑闸] prereg ok`）。
- 单变量轴 = `AGENTFRAMEWORK_RECOGNITION_VERDICT`：**T = 未设（产品缺省 on = 出口打点落地）** / **C = 显式 `off`（= 旧行为：不发该面打点）**。
- 夹具逐字复用 R583：`fixture-shapes-line1.txt` sha `c98f8ab3e8a49acb5363ae62920fca9174b25dced7a8430dcb1870347cb05a8d` ∧ 轮序 `turns-S0.txt` sha `9dc9511f1cb170820beaa661652207e9d75ee1e89b5282954a4fc735e991ba10`；`data/nlp` 跑前置入、跑后**复原为 absent 且回读断言**（无 `EXIT` trap ⇒ 不会覆盖产物）。
- 起臂前置：key 装载（`${#AGENTFRAMEWORK_KEYS_DEEPSEEK}` 校验，值不落盘）+ 远端预检 `http_code=200`（`gate-pre-r608.txt`）；6/6 臂 `rc=0` 严格串行。

## 3 真机读数（6 臂）

| 臂 | rep | 出口事件 | 覆盖 | abstain | 标签样本 | 调用 | 新算 prompt | completion | 判定面 basis 序列 |
|---|---|---|---|---|---|---|---|---|---|
| T | 1 | 2 | 2/2 | 1 | `repeat` / `abstain` | 3 | 6,818 | 2,481 | `pass→remote` / `repeat→local` |
| T | 2 | 2 | 2/2 | 1 | `repeat` / `abstain` | 1 | 4,228 | 866 | `pass→remote` / `repeat→local` |
| T | 3 | 2 | 2/2 | 1 | `repeat` / `abstain` | 2 | 5,295 | 1,200 | `pass→remote` / `repeat→local` |
| C | 1 | 0 | — | 0 | — | 2 | 5,378 | 2,593 | `pass→remote` / `repeat→local` |
| C | 2 | 0 | — | 0 | — | 8 | 62,041 | 5,721 | `pass→remote` / `repeat_no_replayable_prev→remote` |
| C | 3 | 0 | — | 0 | — | 3 | 6,895 | 1,533 | `pass→remote` / `repeat→local` |

出口形态（T 实读，逐轮一行）：`{label, abstain, evidence=basis=…;face=…;len=…;sha16=…, render="<label>|<evidence>", route}`（样本见 `verdict-r608.json:checks_posthoc.outlet_shape_samples`）。
成本三列**只作参考**：池化 T = 6 调用 / 16,341 新算 / 4,547 completion；C = 13 / 74,314 / 9,847 —— 摆动主导（C r2 单跑次 8 调用 / 62,041），**不得作轴效应**。

## 4 判据逐条（预注册原样）

| 判据 | 结果 | 读数 |
|---|---|---|
| P1 治疗 >0 | **PASS** | T×3 三键 = 事件[2,2,2] / abstain[1,1,1] / local[1,1,1] |
| P2 对照 ==0 | **PASS** | C×3 三键 = 全 0 |
| P2 消融逐位等价 | **FAIL（唯一红项）** | rep1 PASS / rep2 **FAIL** / rep3 PASS |
| P3 出口覆盖 | **PASS** | 覆盖 [2,2,2] == 轮数 2；abstain 率首读 **0.5** |
| P4 恒前缀冻结 | **PASS** | `F_env.prefix.chars` = 15291 ∧ `check_cmd` rc=0；命中率**未测** |
| P5 有牙 | **PASS** | 非平凡（T≠C）∧ negctl 交换臂 ⇒ P1/P2/P3 翻红 |

**P2 失败定因（如实，不当轴缺陷）**：rep2 的 C 跑次走 `gate:repeat_no_replayable_prev→remote`（上一轮模型回复形态不同 ⇒ 无回放源），且该跑次调用数 8 vs T 1（新算 62,041 vs 4,228）⇒ **执行面摆动**，非出口轴效应。处置按协议 §3「摆动 ≥ 效应 ⇒ 加 reps/扩窗（禁调阈值）」；产品改动**不回撤**（P1/P3/P4/P5 全过 ⇒ 落地未证伪）。

## 5 `checks_posthoc`（事后单列，**不入 verdict**）

- 可比域形态（P2 的正确形态）：逐 rep 逐位等价 **2/3**（rep1/rep3）∧ turn1 读数在 **6/6 臂唯一**（`mechanical:pass→remote`，机械决定、与模型无关）⇒ **口径可用**；不可比轮 = rep2（见上）。
  下一轮预注册改为**分层（可比域）判据**，**阈值与判据集不变**（禁事后调阈值）。
- 只读性（单测面）：`RecognitionVerdictTests` 断言 `RecognitionOutlet.Render(...)` **不改动** `NlpGate.Counters` 读数（出口只读 ⇒ 判定链零回归的机理）。

## 6 AOT 面（构建/发布形态，协议 §2 环 6）

**JIT Release 构建**：`dotnet build src/agent.host/agent.host.csproj -c Release` ⇒ rc=0 · `10 Warning(s)` · **`0 Error(s)`**（读数落盘 `eval/rover/r608/build-jit-r608.out.txt`；`.log` 后缀被 `eval/rover/.gitignore` 吞 ⇒ 用 `.out.txt` 保证入档）。
`dotnet publish src/agent.host -c Release -r linux-x64 -o …/pub_r608`（禁 `-p:PublishAot`）：**rc=0 · IL 警告 0 · error 0** · 原生 ELF **19,739,568 B**（两次发布尺寸相同）。
**生产档装载冒烟**（仓库外 cwd `/tmp/r608aot`、`env -i`、真 key、一轮夹具）×2 次：均 **rc=0**（真回复，`promptTokens=4795/4779`、`llmModel=deepseek-flash`），且仓库遥测中**新面 `recognition_verdict` 随 AOT 产物发出 ×2**（`2026-09-20T23:10:24Z` / `23:16:59Z`，各 1 行，`abstain=1`、`route=remote`）⇒ **出口在发布形态下可用**（非 JIT-only）。
诚实边界：①冒烟进程把 telemetry 追加在**已记录臂偏移之后**；判据按字节偏移切片，不受影响。②**AOT 发布产物 sha256 不跨次稳定**（两次发布尺寸同为 19,739,568 B、内容不同：`3f7873b8fd173868…` vs `4bfcbb9dc22f9014…`）⇒ 该 sha 只作**单次产物留痕**，**不作同源身份锚**；同源判据用「尺寸 ∧ rc ∧ 冒烟新面发出」三件。（JIT `agenthost` apphost 78,256 B 亦为启动器、非逻辑本体 ⇒ 逻辑本体是本轮重建的 dll 集。）

## 7 门禁

形式门禁（`VerificationForm|SkillGeneralization|DevPlanDocRef`）· 全量单测 · API 基线 `+14 / −0`（仅本轮成员：`RecognitionOutlet.*` / `RecognitionVerdict.*`，`BASELINE_WRITE=1` 重生成后 diff 只含本轮 14 行）· `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· `decl_sweep.py --check` **0 漂移（30 件）**。

> **门禁读数**（`bash eval/rover/r608/tests_r608.sh`，日志 `/tmp/r608-tests.log`）：
> 全量单测 **1953 通过 / 1 失败 / 1954 计**（38 s）；**唯一红 = `PromptCacheChannelTests.溯源_夹具必须是活遥测的子集不得凭空造数`（`KeyNotFoundException` at `PromptCacheChannelTests.cs:170`）**。
> **前态同形已机检证明**（非本轮引入）：按起臂前字节切分 `data/telemetry/host.jsonl`，`llm_call` 缺键行 = **2 行，全部落在起臂前字节**（`2026-09-20T20:17:52Z` / `20:17:59Z`，键集缺 `prompt_tokens/cache_hit_tokens/cache_miss_tokens`）；本轮新增字节的 20 行 `llm_call` **缺键 0** ⇒ 该红与本轮改动无关（历史同形）。
> 形式门禁（`VerificationForm|SkillGeneralization|DevPlanDocRef`）**14/14 通过**（rc=0）。

## 8 文献小步（≤3 检索式预算已用满）

3 式（`"selective prediction abstention"` / `"open-domain intent recognition"` / `"abstention calibration LLM agent"`，均 `--category cs.CL --max 6 --sort date`）**3/3 零结果** ⇒ **采信 0 / 候选 0 / 证伪 0 / 顺延 0**（属「0 结果」非「预算被吃满而顺延」）。
台账追加见 `docs/research/lit-review-ledger.md` §10（含器具观察一行：短语 ∧ category 组合过窄，按预算未追加以免越限）。**连续 0 采信 = 第 1 轮**（反空转阈值 3 轮）。

## 9 诚实边界

1. 无质量对照臂（codex）⇒ **不宣称任何质量/成本降幅**；成本三列标「参考」，且摆动主导。
2. abstain 率 0.5 = **首读基线**（无历史值可比，无阈值）；出口闸（abstain 率↓）判据留给 R609。
3. 恒前缀命中率 ≥97% **未测**（REPL 面无该口径）。
4. `P2` 预注册判据**过强**（把执行面摆动轮纳入比较域）⇒ 判 FAIL 并按可比域形态单列；不改阈值、不翻案。
5. 单窗口每臂 n=1 不作能力结论；出口面读数只证「接线 + 可消融 + AOT 可用」。
6. 本轮**未**跑 codex 同题面质量对照 ⇒ 主线判据（质量 vs 外部真值）本轮**未行使**。

## 10 候选台账（逐候选 · 状态 · 原因）

| 候选 | 状态 | 原因 |
|---|---|---|
| RF0004.1 出口落地（本轴） | **做** | 真机 6 臂 + AOT 冒烟，证据在案 |
| 只读消融（轴关=旧行为） | **做** | C 臂 == 旧行为（该面 0 事件） |
| AOT 面 | **做** | rc=0 / IL 0 / 冒烟新面发出 |
| 可比域形态 T/C 逐位等价 | **做** | `checks_posthoc`（预注册判据照原样判 FAIL） |
| codex 质量对照臂 | 未做 | 出口落地轮无质量对照项（跳步声明一行） |
| 命中率（恒前缀缓存） | 未测 | REPL 面不产该口径 |
| backlog exp2 menu 问询协议 / exp3 步骤对齐 / exp4 工具申请 / exp8 skill 蒸馏 | 未做 | **不同轴**（各自独立计划项）；本轮唯一单变量 = 出口轴（协议 §1 唯一单变量硬约束） |
| R609 出口闸（abstain 率阈值 + 分层判据） | 未做 | 需先有首轮基线（本轮 0.5 已落盘） |

## 11 收口五件

1. 轮工件：`eval/rover/r608/{dag,prereg,run_r608.sh,judge_r608.py,aot_r608.sh,tests_r608.sh,offsets-r608.json,verdict-r608.json,verdict-r608-negctl.json,pre-arm-state.txt,arm-meta.txt,gate-pre-r608.txt,report-r608.md}`
2. 证据文档：`docs/evidence/RF0001/R608-recognition-outlet.md`
3. registry 行：`docs/verification-registry.json`（+ `updated_round`）
4. kpi 行：`eval/capability/kpi.jsonl`（带 `baselines` id 列表）
5. 提交：逐名列名（禁 `git add -A`）
