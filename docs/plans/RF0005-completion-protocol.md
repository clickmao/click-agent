# RF0005 · 迭代完成协议（自驱环 · 决策规则 · 排期 · DoD）

> 缘起（用户令，2026-09-21 逐字）：**「我希望你自己形成一套迭代方案来完成这个项目」**
> ⇒ 本文件是**完成期的执行协议（runbook）**：把 `docs/reports/iteration-master-plan.md`（宪法/设计面）与
> `docs/plans/RF0004-three-capability-development-plan.md`（三能力排期面）落成**每轮照做的步骤 + 可机检的决策规则**。
> 依赖面：`iteration-master-plan.md` §0-0 铁律 10–13 · RF0004（三能力唯一验收面）· RF0001 §0/§3/§6（v1 判据）·
> `eval/capability/baselines.json`（可观测基准台账，14 条）· `tools/roundcheck/roundcheck.py`（audit/preflight）· `eval/capability/status_gen.py`（`--check`）

状态：**活计划**（§0 的「现读数」列每轮刷新；历史结论一律不改） ｜ 建立轮次：**R607** ｜ 机检口径：`status_gen.py` / `roundcheck.py` / `baselines.json`

---

## 0. 完成定义（DoD）：七面，全部机检

「项目完成」= 下表七面**同时**为绿；任一面红 ⇒ 未完成，不得对外称「v1 完成」。阈值一律引
`eval/capability/baselines.json` 的基准 id（**禁把本轮读数当阈值**）。

| # | 面 | 判据（机检口径） | 阈值/出处（baselines id） | 现读数（R606 收口后） | 状态 |
|---|---|---|---|---|---|
| 1 | **质量** | 对 codex 同题·同夹具·同窗的**配对逐窗差** | 中位 ≥ −2（`truth-vs-t-arm`）· 整题全对 ≥ 真值（`truth-whole-task`）· reps≥3 报逐窗+极差 | T 7/9 vs C1 7/9；D 逐窗 [−11,0,0] 中位 0；**J2 收敛反向 2 vs 6 · J4 整题全对平** | **未达标** |
| 2 | **成本** | 调用数 / 新算 prompt / completion **三列分列** | 三列均 ≤ 真值（`cost-calls`·`cost-newprompt`），两形态并列**禁跨轮相减** | 调用 21 vs 真值 59 ✔；新算 18,201 vs 32,189 ✔；但同臂 C 仅 15 / 11,139（+40% / +63%） | **未达标**（须无代价） |
| 3 | **恒前缀缓存** | 前缀 chars/sha256 冻结（只许加厚）+ 命中率 | ≥0.97（`cache-hit-floor`）· 冻结 `fp-constants`（chars=15291 / `f1280f71…d4a`） | 命中 v_all：T 0.9167 / C 0.9288 / 真值 0.9525；前缀未破 | **未达标** |
| 4 | **上下文精排** | NDCG@k（主）· MRR · Precision@k · Recall@N=1.0 + 负控 `LexicalRerankScorer` | NDCG@k ≥0.8 / MRR ≥0.6 / P@k ≥0.8 / R@N=1.0（`rerank-four`） | **R623 有读数**：T/C NDCG@10 中位 0.5000（63/90 并列 ⇒ 中位被钳制）· MRR 均值 0.4772→**0.4929** · 配对 **27↑/0↓/63=**（零回归）· R@N **0.75**（前置天花板）· 生效遥测 `RerankApplied` 120/120（非孤岛）· 负控 NEG 中位 0.0000 / POS 1.0000。**R624 形态对齐**（召回面）：R623 申报「生产 DI」经机检**证伪**（未设 `EmbeddingFunction` ⇒ 词袋哈希兜底）⇒ 生产形态下同一冻结件读数 = R@N **0.8083**（K=50 单变量 **+5.83 pt** / +7 条 ≥ Δ_min 6 ∧ 兜底档零回归）· K=200 **0.9000** · **全池 1.0000（结构性不可召回 0）**；零向量负控 **0.7417** < 兜底 0.7500（有牙）；30 条未召回五分守恒（两者皆需 **14**） | **未达标**（四阈值：R@N=1.0 在**生产形态全池**达成 ✓；同池宽 K=50 ≥0.90 未达；P@k ≥0.8 在单 gold 分级下上界 = 1/k ⇒ 结构性不可达；池宽=成本轴且成本未测）|
| 5 | **判据分辨率** | 有效窗数（预注册判定可判） | ≥2 有效窗，否则 rc=3 ⇒ 判据不可判（`res-min-windows`） | R606 有效窗 3；R603 曾 valid=1 ⇒ 不可判 | **临界** |
| 6 | **工程面** | AOT 0 IL · 全量测试 · 零反射 · API 基线 · 结构不变式 | 全绿（`eng-aot-zero-il`·`eng-full-tests`） | AOT rc=0 / 19,735,472 B；全量 1942/1943（1 已知前置红）；形式门禁 **14/14**（Debug 过滤集现读；R606 那次 21/21 系另一配置读数，已按现读改正） | **临界**（1 前置红） |
| 7 | **对外与自升级** | 三能力出口闸（RF0004）+ `frontendapi` 对外 + `LearnedShape` 补丁生效 | 见 RF0004 五格出口闸（`cap-recog`·`cap-orch`·`cap-gen`·`cap-selfup`） | 三面**均未接线**（`NlpGate` 无统一出口 · `TaskKindHint` 5 档无 Generation · `ModelQueueAdapter.cs:154` 旧文本动作环） | **未达标** |

> **口径警告**：早前汇报的「≈33%（旧 v1 四条判据等权）」**已随范围扩展失效**，不得再引用——本表才是进度唯一权威面；
> 百分比重估只在 §8 的「每 10 轮 DoD 复核」里做，且必须写明权重与口径。

---

## 1. 迭代单元：一轮 = 一个单变量 + 一次可证伪的判定

七条硬约束（缺一即不算「一轮」，记 `裸轮`）：

1. **唯一单变量**：env 开关**或**代码改动二选一；禁打包多项（打包 ⇒ 归因不可分）。
2. **臂表 ≥3**：`T`（单变量 on）· `C`（轴关 = 旧行为，须**逐位等价**机检）· `C1`（外部真值 codex，同题同夹具同窗）。
3. **窗集不相交**：与历史轮窗集不得复用；同件扩窗（如 w193..w195 → w196..w198）允许，重复用窗禁止。
4. **reps≥3**：单窗=噪声 ⇒ 报**逐窗 + 中位 + 极差**；失败窗标 `unreliable` 并单列。
5. **预注册先行**：`eval/rover/r###/prereg-r###.json` 必含——单变量 / 臂表 / 判据 / **阈值出处（baselines id）** / 证伪条目 2–3 条。
6. **机制面与能力面分开判定**：机制 PASS **不得**掩盖能力 FAIL（R600 教训）。
7. **收口五件**：轮工件（`eval/rover/r###/`）· 证据文档（`docs/evidence/`）· registry 行 · `kpi.jsonl` 行（**带 `baselines` id**）· 逐名列名提交。

---

## 2. 固定环（每轮按序照做；跳步必须在报告写「跳步 <名称> <一行原因>」）

| 步 | 动作 | 命令 / 出口证据 |
|---|---|---|
| 0 | **起手闸**（环境）| `python3 tools/roundcheck/roundcheck.py preflight --round R<next> --min-avail-mb <上轮 swing MB> --min-disk-gb 1 --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK`；先 `set -a; . ~/.agentframework/keys.env; set +a`；清 `VBCSCompiler`/`MSBuild`/`pyright` 后记 MemAvailable |
| 1 | **主线提醒**（只出 1 行）| 读 `iteration-master-plan.md` §7 + RF0004 + 上轮 `verdict-r###.json` ⇒ 当前轮次 + 差距 + 下一步 |
| 2 | **选靶**（缺口归因）| 上轮逐例归因表（缺口集中族优先）；禁预言式修复；**一问题不吃多轮**（R2）|
| 3 | **文献小步** | `python3 '$HOME/.hermes/skills/research/arxiv/scripts/search_arxiv.py' '"<短语>"' --category cs.CL --max 6 --sort date`；预算 arXiv ≤3 query / 全文 ≤2 篇 / 间隔 ≥4s；追加 `docs/research/lit-review-ledger.md`（`io.open(...,'a')`）；**只产机制假设** |
| 4 | **预注册** | 写 `prereg-r###.json`；阈值引 baselines id；证伪条目 ≥2 |
| 5 | **产品侧最小改动** | 复用既有组件；**零新增夹具**；动产品码前先写「改哪一格读数」；未放行分支不许动 |
| 6 | **构建/AOT** | `export DOTNET_ROOT="$HOME/.dotnet"`；AOT publish（rc=0 / 0 IL；**禁加 `/p:PublishAot`**）+ 定向测试 + 全量 `timeout 560 dotnet test src/agent.tests/agentframework.tests.csproj` |
| 7 | **真机跑** | 两侧夹具 md5 一致才开跑；reps≥3；前台 `timeout` ≤600；同时只跑一个 `llama-server` |
| 8 | **判决** | `judge_r###.py`：机制/能力分判 + 铁律 11 前置器 rc（`eval/rover/r507pre/exec_precondition.py --round r###`）+ 有效窗计数 + `unreliable` 单列；**证伪命中 ⇒ 收窄/回滚**（R1）|
| 9 | **收口与汇报** | 证据文档 + registry 行（pin 现算 / 尾 LF / `updated_round`）→ 器具漂移处置 → `status_gen.py --check` **必须 PASS** → 形式门禁 → **逐名列名** `git add --` + commit → 六格汇报（≤3 行 + KPI 表）|

**形式门禁**（改证据/登记表后必跑）：
`env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q`

---

## 3. 决策规则（自决 + 升级边界）

| 规则 | 触发 | 动作 |
|---|---|---|
| **R1 证伪即收窄** | 预注册 falsification 条目命中 | 该轴降为观测项，撤回未提交 src ⇒ **净产品改动 = 0**（只入轮工件）|
| **R2 一问题不吃多轮** | 同一缺口连续 3 轮无改判 | 换杠杆（换面/换族/换判据形态），**禁加轮**；缺口族优先做「可执行前置步骤」使其从静默错步变硬证据 |
| **R3 分辨率优先** | 有效窗 <2 / `valid=1` | rc=3 **停链** ⇒ 先造窗集（真值自败窗剔除并单列），**禁下调阈值** |
| **R4 真值非硬上限** | codex 自身掉线/自败 | 该窗标 `unreliable` 剔除后重算；表内标注（`truthdrop` 证）|
| **R5 摆动 ≥ 效应** | 极差 ≥ 待测效应 | 加 reps / 扩窗，**禁调阈值** |
| **R6 器具改 ⇒ 重审重钉** | 改了任何被 pin 的器具（如 `status_gen.py`）| `python3 eval/capability/decl_sweep.py --apply` + registry 行 `instrument_sha12` 重钉 + 负控复跑；否则形式门禁 R2e 红、EXP1-Q39 闸**拦提交** |
| **R7 判据器跨轮改版禁相减** | 判据脚本改动 | 同轮报正/负控；口径变更须同轮改**作业 prompt**（口径令）|
| **R8 预算守卫** | 报告/台账膨胀 | 回复 ≤3 行 + 六格；RAG ≤120 / 记忆 ≤400 / 里程碑 ≤2（kpi 行 `t` 预算）|
| **R9 升级用户（仅三类）** | ①方向/范围裁定 ②放行（产品分支·预算·推送）③外部真值不可得（key/网络）| 其余**一律自决并留痕**；「可自决却问」= 无效提问（目标 0）|

---

## 4. 排期：里程碑 × 轮 × 出口闸（唯一排期面 = RF0004；本表只做进度映射）

| 里程碑 | 轮 | 唯一单变量 | 出口闸 | 映射 DoD 面 |
|---|---|---|---|---|
| RF0004.0 盘点+打点 | R607 | 零产品改动：三面打点齐全 | 打点治疗>0 ∧ 对照==0 ∧ 前缀 ≥97% | 3 · 7 |
| RF0004.1 开放域识别 | R608–R609 | 统一出口 `RecognitionVerdict{标签\|abstain,依据}` | abstain 率↓ ∧ 命中正确率 ≥基线 ∧ 远端调用不升 | 7 |
| RF0004.2 多轮工具编排 | R610–R612 | 动作候选进 R1 契约（前缀只加厚）| 调用 ≤ 旧臂 50%（request_id 去重）∧ 质量 ≥ 旧臂 | 1 · 2 · 7 |
| RF0004.3 生成类 | R613 | `TaskKindHint.Generation` + 产物验收器 | 质量不降 ∧ completion 不升 ∧ 分流比有分离 | 1 · 7 |
| RF0004.4 闭环自升级 | R614–R615 | 远端回执 ⇒ `LearnedShape` 补丁 | 补丁生效率>0 ∧ 无补丁逐位等于旧行为 | 1 · 7 |
| DoD 缺口（并行面） | +1–2 | 判据分辨率收口（窗集重造，R3）| 有效窗 ≥2 且不可判即 rc=3 | 5 |
| DoD 缺口（并行面） | +1–2 | 精排四项实测（NDCG@k/MRR/P@k/R@N）| 四值有读数 + 负控分离（**R623 已行使**：有读数 ∧ 负控分离 ∧ 结论 = 未达标 ⇒ 残余缺口 = 分级加厚〔须放行〕与召回面）；**召回面残余已闭合（R624）**：形态对齐后 生产形态全池 R@N **1.0000**（结构性不可召回 0）∧ 同池宽单变量 +5.83 pt ∧ 负控有牙；剩余 = 分级加厚（须放行）与池宽**成本轴**（成本未测）| 4 |
| DoD 缺口（并行面） | +2–3 | 质量缺口（wythoff 冷集构造层「可执行前置步骤」）| 配对差中位 ≥ −2 ∧ 整题全对 ≥ 真值 | 1 |
| 交接 | +1 | 跑分（同题 reps≥3 vs codex）+ 发布清单 | 报告 + tag | 全部 |
| **RF0006 独立调研面（并行轨）** | QR1–QR4（**不占主线轮次**） | 三值/低比特压缩 gguf：换原生三值件 → 判别位重跑 →（不过则）混精 | 体积 ≤现役 70% ∧ 判别位 `acc 1.000` ∧ `假跳 0/14` | 3 · 6 |

**剩余轮数区间**：三能力 10–14 轮（**放行口径 5–7 轮**：每轮都能动产品侧）＋ DoD 缺口 4–7 轮 ⇒ **总计 9–15 轮**（跑分另计 1–2 轮）。
**RF0006 为并行独立调研轨，不计入上表轮数**（用户令 2026-09-21；唯一权威面 = `docs/plans/RF0006-ternary-gguf-compression.md`）。
两个口径差 = **放行率**，不是轮数；阻塞项 = 判据分辨率（R3）。

---

## 5. 资源与并发纪律

- **内存**：MemTotal 3,659 MB；`llama-server` **同时只跑一个**；起臂前清 LSP 并记 MemAvailable 前后差。
- **磁盘/余量**：以 `preflight` P4 现读为准（禁引历史读数）。
- **同窗禁构建**：兄弟会话写同仓时本侧**零写入/零构建/零提交**（让行）；本侧排轮期禁 `dotnet test`/`publish`（会把起手闸余量抬到千 MB 级：r605 swing 1091 MB vs 洁净 r603 285 MB）。
- **推送暂停令在效**：禁 `git push` / `gh api` 写 / 镜像上传；只允许本地 commit；提交**禁 `git add -A`**（逐名列名）。
- **凭据卫生**：key 面自备（`set -a; . ~/.agentframework/keys.env; set +a`），值不入仓库/prompt/git config，对话按 `[REDACTED]`。
- **前台 `timeout` ≤600s**；长任务用 `background=true` + `notify`，勿用 `sleep` 长等。

---

## 6. 红线（不做什么）

1. 禁预防性机制轮 / 预言式修复（无真实缺口的机制不立项）。
2. 禁新增夹具与额外开发（要动码先说明「改哪一格读数」）。
3. 禁 `git add -A`；禁 push / `gh api` 写。
4. 禁跨轮相减（成本/质量）；禁把本轮读数当阈值。
5. 禁封闭系统自证（只读本仓读数/自报 ⇒ 记为「未自检」）。
6. 禁改判据器/器具而不重审重钉（R6）。
7. 禁 rewrite 历史凑绿：`roundcheck audit` 的 R6 裸计数红**留红不凑绿**，只归档不重写。
8. 禁「差不多就行」式结论：未测就写「未测」，失败就写失败与分类。

---

## 7. 失败模式库（症状 → 定因 → 处置 → 例证）

| 症状 | 定因 | 处置 | 例证 |
|---|---|---|---|
| 缺口 100% 集中单族 | 冷集构造层「可执行前置步骤」未落地 ⇒ 静默错步 | 产物内加「落点必须属冷集」断言，错步变硬证据（R2）| R585–R605 全 `wythoff` |
| 主判据无分辨率 | 真值自败窗被剔除 + 窗集过小 | rc=3 停链先造窗集（R3）| R603 `valid=1` |
| 单变量结构性 inert | 模板/上游不支持该参数 | 消融前先证「变量可生效」| R448 `--reasoning-budget` |
| 空正文/无输出 | `tool_calls ∧ max_tokens=None` | per-call 归一 + 去常量反事实 | 多轮 |
| 闸静默 fail-open | `STAGE_MANIFEST` 未 export ⇒ 闸未开 | 起手前必检导出 | Q31 |
| 器具漂移拦截提交 | 改了被 pin 的器具而未重钉 | `decl_sweep --apply` + registry 重钉 + 负控（R6）| 本轮（`status_gen.py`）|
| 台账/证据假路径 | `artifacts` 写了不存在/仓外路径 | 只许仓内相对路径且存在；发现即更正并留痕 | R606 kpi 行 |
| 起手闸余量虚高 | 同窗构建抬高 PREV_SWING | 排轮期禁 build/publish | r605 1091 MB vs r603 285 MB |
| 起手闸**拒开**（rc=2，轮未开跑）| 顶棚装不下下限 ⇒ 闸 `fail-closed` | 清 LSP（`VBCSCompiler`/`MSBuild`/`pyright`）后**重取 ceiling**（禁降标准强开）；**rc=2 ⇒ 不算轮**，不得当轮读数 | R606 首启 04:30:29 `顶棚 2735 装不下下限 60MB`；清场后 04:31–04:41 跑完 |
| 全绿但没进步 | 机制 PASS 掩盖能力 FAIL | 机制/能力**分判**（§1.6）| R600 |
| 汇报膨胀 | 细节写进回复 | 细节只落盘；回复 ≤3 行 + 六格 | 用户令 2026-09-17 |

---

## 8. 自检与漂移检测（元层，防「跑得动但跑偏」）

- **每轮**：`python3 eval/capability/status_gen.py --check` ⇒ 期望 `PASS (违规 0 / 基准漂移 0 / 缺源 0)`；`roundcheck audit --round R###`（R6 红留红）。
- **每 5 轮**：元审计 = 口径漂移（`docs/` 内政策行 vs 作业 prompt 是否同源）· 器具漂移（`decl_sweep` 0 漂移）· 文档 pin 漂移（`roundcheck` R4）。
- **每 10 轮**：DoD 七面**全列复核** + 百分比重估（须写明权重与口径）+ 剩余轮数区间刷新。

---

## 9. 停机与交接

**停机条件** = §0 七面同时为绿 ∧ 三能力出口闸达。停止所有优化轮，转交接：

1. 冻结 AOT 产物（记 sha12 / 尺寸 / 0 IL）+ 前端 `frontendapi` 对外可用性实证；
2. 跑分（同题 reps≥3 vs codex 同窗）出报告 + `docs/reports/status.json` 终版；
3. 发布清单（产物 / 接口 / 文档 / 基准台账）一次成文；
4. 未闭合项**如实列出**（不得隐藏），并标「已知边界」而非「已完成」。

---

## 10. 本文档纪律

- §0「现读数」列**每轮刷新**；历史结论与历史读数**一律不改**（改动留痕：新值 + 日期 + 轮号）。
- 改本档须重算其 pin；**改口径必须同轮改作业 prompt**（口径令），否则视为未落地。
- 本档不新造器具、不新造夹具：命令全部来自既有件（`roundcheck` / `status_gen` / `decl_sweep` / `exec_precondition` / 各轮 `run_r###.sh`·`judge_r###.py`）。
