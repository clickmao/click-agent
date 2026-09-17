# AgentFramework 改进文档 (improvements.md)

> **记录规则 (2026-09-08 重梳)**: 顶部 = 最新版本, 逐版本向下递减; 每节格式统一
> (版本 / 日期 / 状态 / 主题 / 完成记录 / 基线)。v7.x 为历史遗留版本号体系 (v0.x 前身),
> 原始记录见文末「历史遗留」区, 详情走 git log。
>
> **⚠ 文档严谨性铁律 (2026-09-09 用户钦定, 长期有效)**: 凡【以文档为驱动的循环开发迭代方案】
> 中的文档 (README 双语 / api.md / architecture.md / CLI指令说明.md / improvements.md 等),
> 任何修改必须做**全文整体/大区域合法性校验** — 标题与内容对齐 (版本号、批次趋势行归属)、
> 数据时效 (测试数/批号/评测口径)、版本引用一致性、死链检查; **禁止只改局部不做整体校验**。
> 空间位置相邻但语义不同段的错挂 (如旧版本标题下挂新数据) 视同违例。

## R528 · 2026-09-17 · 状态: **完成（归因修正 + 纪律修复；铁律 11 前置器 rc=1 由**外部真值臂**造成 ⇒ 成本读数标「参考（未可验收）」）** · 主题: **产物落位与自验纪律 —— R525 w3 的 0/58 不是代码缺陷（同一棵树换 cwd 实跑 58/58），是「包写到工作根之下多一层 + 自验也在那层做」**

- **因果链**: R525 w3 两侧 agent 臂 0/58（同窗 codex 58/58）曾被读成「产物不可运行/能力不足」。逐调用取证：该臂 8 调用/3 步把 `games/` 包写到 `<工作根>/sols/games_pkg/games/`（step1 `mkdir -p` 已 rc=126 未处理），step3 `cd sols/games_pkg && python3 -m games life` rc=0 即自认完成；而验收形态是**工作根**下 `python3 -m games <id>`（判据器以 cwd=树根 + `PYTHONPATH=wd` 启动）⇒ 包不可导入 ⇒ 0/58。**实跑复验**：同一棵树以漂移目录为 cwd 跑同一隐藏用例脚本 ⇒ 58/58 ⇒ 归因从「代码质量」纠正为「产物落位 + 自验位置」。
- **交付**: 动作环纪律第 6 条「产物落位与自验」（`ActionLoopDiscipline.cs`；工作根 + 题面相对路径 + 工作根自验 + 自验 rc≠0 不得收尾）+ 单测锚 2 条（`R522ContextDisciplineTests`）+ 器具四件（`mount_check_r528.py` 挂载取证 / `layout_census.py` 归档布局普查 / `kpi_r528.py` 三列分列 / `run_all_r528.sh` 五窗驱动）+ 登记表两行（`internal.artifact-placement-selfverification-r528` L4 · `internal.artifact-layout-census-r528` L3）。
- **读数**: 五窗同窗对照（同一 AOT `8f801491…` / 同一题面 sha `516f3208…` / 58 用例）—— **本侧 A1-on 5/5 窗整题全对 58/58**；挂载 **5/5**（A1-on system 9,968 = A0-off 9,434 + 2 + 532 字符常量块；块 sha `16efa2f0` 五窗恒定；条目 [1..6]）；布局漂移 **0/5**；**负控**（同一挂载器对 R525 修前 dumps）判红（锚缺失 / 条目 [1..5] / 块 sha `cbc691bb`）；归档普查 30 棵树 = `layout_ok` 26（22 全对，4 真部分错）+ `layout_drift_code_ok` 1（即 R525 w3）+ `missing_artifacts` 3（皆控制臂空产出）。成本三列（调用/新算/completion）A1-on 中位 **7 / 4,269 / 6,035** vs codex **7 / 4,273 / 3,007** ⇒ 调用与新算追平，**completion 仍 2.01×**。
- **基线**: 本侧首次做到该题族五窗整题全对（R525 三窗里有 1 窗 0/58）；AOT `8f801491ef27ed2c…` 15,613,264 B，publish rc=0。
- **诚实边界**: ① **J4 未达成** —— 铁律 11 前置器 rc=1，唯一验收面失败是**外部真值** `w2/codex` 52/58（R523 已立「codex 失败窗不可靠」）；故全部成本读数标「参考（未可验收）」，**不对本轮事后收窄验收面凑 rc=0**（`evidence_scope` v2 只做臂名形态对齐，收窄事实已在 prereg 单列披露）。② 只改一条纪律文本 ⇒ 不宣称能力提升，宣称限为「纪律生效面 = 挂载 5/5 + 漂移 0/5 + 本侧五窗全对」。③ 题集族仅 1 题，跨窗摆动仍是主不确定源（A1-on 调用 6→19、codex 4→29），禁跨轮相减、不宣称 R413 降幅。

## R520 · 2026-09-17 · 状态: **完成（阻断项闭合：影子路径闸 + 编排臂首次可测；同窗对照结转）** · 主题: **编排臂 0/58 的定因与修复 —— 节点把工作区自身位置当相对路径用 ⇒ 工作区内影子副本**

- **因果链**: R519 编排臂唯一读数 0/58 的真因不是能力: 节点 n1 把工作区**绝对路径裁成仓根相对串** (`eval/rover/r519/run-0917-144416/orch/ws/games/life.py`) 当工具 path 用 ⇒ 端口按「相对根」解析 ⇒ 落到 `<ws>/eval/rover/…/ws/games/life.py` (影子副本), 而 `write_file` 回 ok + 回显**请求串** ⇒ 节点读到另一份文件, 自述「环境预置的另一版实现, 我的内容未持久化」(`n1.md` 原文) ⇒ 范围闸判 `out_of_scope` ⇒ n1 Failed, n2–n5 未执行。
- **交付**: `WorkspaceActionPort` 影子路径闸 ((a) 以根完整路径开头 或 (b) 前 k 段 (k≥2) == 根后 k 段; **单段同名不判**; 报文给落点 + 建议改写; 与 P1 同闸 ⇒ 可消融) + 节点提示词第 5 条纪律 + `R520ShadowPathTests` (正控/负控/消融臂) + 磁盘级独立机检 `shadow_check_r520.py` + 登记表两行 (`agent.shadow-path-gate` / `external.contrast-orch-arm-r520`)。
- **读数**: 节点 **1/5 → 5/5 Completed**; 范围违规 **1 → 0**; 影子文件 **1 → 0** (机检 RED → GREEN); 58 用例 **0/58 → 9/58** (用例级, 异窗不可相减); 单测 **40/40**; 判据器对 R519 同一 ws 复跑 `rc=1/total=58/passed=0` 逐位相同。
- **基线**: 编排面首次产出可比读数 (AOT `/tmp/pub_r520/agenthost`, 15,609,168 B), 但**整题全对率仍 0** ⇒ 按铁律 11 未过可验收前置, 降幅读数留待同窗三臂。
- **诚实边界**: 本轮无同窗两侧对照 (铁律 11 前置器 `--round r520` 报 `DISCOVER_FAIL rc=3`) ⇒ **不宣称任何 token/调用降幅**; 仓根 `./life.py` (mtime 04:06) 属本轮窗口**之前**的历史残留, 与本缺陷无关。

## R519 · 2026-09-17 · 状态: **完成（轮节回填：R519 此前无节，据其落盘产物复核）** · 主题: **游戏类多文件长任务三臂同窗（单轮 58/58 ×3 窗 / codex 58/58 / 编排 0/58）**

- **回填依据**: 轮志产物 `eval/rover/r519/run-*/` + 预注册 `prereg-r519.json` + 提交 `8342649`; 本侧复核 = 同一判据器对同一 ws 复跑**逐位相同** + 影子机检 RED。**该轮由同 gateway 的兄弟会话实施**, 本节只登记我复核过的读数 (归属如实, 不冒充本侧成果)。
- **读数**: 单轮臂 58/58 (×3 窗) · codex 外部真值 58/58 (打平) · 编排臂 0/58 (n1 越界写入 fail-closed, n2–n5 未执行)。
- **诚实边界**: 编排臂的 0/58 经 R520 定因后改判为**路径框架缺陷**而非能力读数; 跨窗不承诺。

## R514 · 2026-09-17 · 状态: **完成（候选②器具化 + 候选①口径切换；候选③④如实结转）** · 主题: **夹具自检器具化：题面-判据一致性机检器 + 主判据切「不必要的远端调用数」**

- **因果链**: R512 的 p4 夹具缺陷（题面未写 `--now` 缺省 ⇒ 8/12 用例依赖题面外约定 ⇒ 内含外部真值的三臂同败、判据无区分力）**靠人工定位** ⇒ 本轮把它机械化，使后续每一轮对照在进臂前就能自查。
- **交付**: `eval/rover/r514/statement_contract_check.py`（D1 未声明选项 / D2 依赖未写明缺省（binding·masked·spawn_site 子分类）/ D3 未声明错误码 / D4 未声明输出键；rc 0/1/2/3 分层，2 = 器具缺陷 fail-closed）；`nc_statement_contract.py`（8 臂负控阶梯）；`check_criteria_r514.py` + `shadow_selftest_r514.py`（候选①）；`prereg-r514.json`（器具与冻结输入 sha256）。
- **读数**: p4 题面 v1 ⇒ predicted binding **8 条 == R512 真机 6 跑次众数失败集合逐字相等**（`binding_eq_observed=true`），`masked=1` 单列（`bad_request_exit2` 只断言错误码 ⇒ 人工定位看不见的掩盖态）；负控 8/8 符合期望、`frozen_fixtures_unchanged=true`；影子自检 9/9。归档回放：R512 的 token 判据在新口径下 `ABSTAIN_N_BELOW_MIN (n=4<5)` ⇒ 由 PASS 降为**弃权**（口径变更）。
- **基线**: 器具校准层的可复现读数，非产品性能读数；产品面基线未变（本轮未跑真机臂）。
- **诚实边界**: 事后锚定校准不作预测命中；D4 在 HTTP 题族分辨力有限；候选③④ 与 `improvements.md` R404–R407 结转（未静默丢失）；R512/R513 窗口禁相减照旧。

## R510 · 2026-09-17 · 状态: **完成（链两端收口 + 主线单点 A/B；验收前置 rc=1 由对照臂造成 ⇒ token 读数标「参考」）** · 主题: **步进事件真发 + 审批通道闭环 + 自检契约泛化（靶点用例 1/3 → 3/3）**

**因果链**：R509 留两处欠账 —— ① `task.progress` 只在 `FrontendTaskRegistry.Progress(...)` 登记, 全链无调用者（前端拿不到步进 = 封闭系统自证）；② `RequestOperationApprovalAsync` 是保守拒绝占位（前端批准/拒绝打不通）。主线（铁律 10）单点缺陷：p3 隐藏用例 `restart_drops_expired` 反复挂 —— 自治自测只覆盖 happy path。三件事同属「链的出站面 + 自治面」⇒ 同轮处理, 一次 AOT 发布（host sha12 `993d0fa548e9`）。

**改动**：`src/agent.modelqueue/ActionProgressObserver.cs`（新, AsyncLocal 绑定出站面, 未绑定零开销）+ `ActionLoop.cs` 每次工具执行后 `ReportAsync`；`FrontendApiChatRouter.cs` chat.send 作用域 `BindProgress` → `task.progress` 事件 + registry；`ApprovalEnvelope.cs`（新）+ `FrontendPromptService` 真审批（requested → respond → responded 收口；超时/拒绝/取消/被覆盖一律不批准）+ `FrontendEventHub.IApprovalReplySink`/`AttachApproval` + 路由 `approval.respond` + `Program.cs` 同源挂接；`SessionBaseline.cs` 二.3 增「契约每条非功能语义（重启后状态/持久化重放/并发原子性/过期清理）要有独立用例」。

**真机 E2E**（`bash eval/rover/r510/run_e2e_frontend_progress.sh`，AOT + frontend-api + 动作环开 + 真模型）→ `E2E_RC=0`，A1–A6 机械判分全绿：事件序 `task.started → task.progress×3 → task.completed`（R509 无 progress）；首条 `step_index=1/tool=write_file/ok=true`；工作区**真出现** `r510_progress.txt`（反伪造）；`state.snapshot.tasks[0]` = `done/step_index=3/current_action=run_command`；`approval.respond(apr-doesnotexist)` → `unknown_approval`（不静默当批准）。

**A/B（同窗·同夹具 md5 `8d13fd53…`·同模型·每跑次独立 session, n=3/臂, 起手闸连续 2 PASS, 预注册于起臂前）**：agentBefore（旧 AOT `fe07205ba3b8`）**1/3** 全对（24/36 用例, 靶点 `restart_drops_expired` 1/3）vs agentAfter（新 AOT）**3/3** 全对（36/36, 靶点 **3/3**）；调用数 7.0 vs 7.0 持平；tokens/轮 91,252 vs 87,057（adapter relay 真值, **标「参考（未可验收）」**）。

**机制归因（如实记，未成立）**：after 臂 2/3 跑次产物自带 `--selftest` 且含 restart 相关用例（`selftest.py` restart_hits=2/3），before 臂 1/3（ab1 hits=4）；**但 before-ab1 自带含 restart 自测仍挂靶点用例** ⇒ 1/3→3/3 只能记作「条款 + 采样」共同结果，**不归因该条款单独作用**（n=3，方差占优）；机制归因留 C3（n≥5 + 逐跑次自测覆盖度编码）。

**验收前置（机器复跑, 非自报）**：`python3 eval/rover/r507pre/exec_precondition.py --round R510` → `SELF_REPORT_AGREES=True`；交付物臂三窗全 12/12 `rc=0 correct=True`；全局 `EXECUTABLE_AND_CORRECT=False / rc=1`，阻塞**全部来自对照臂**（r510ab1 点名 `restart_drops_expired`；r510ab2 点名 11 条）；`SCOPE_SOURCE=None`（prereg 未声明 `evidence_scope`）⇒ **不追溯补写**（禁事后补记），token/调用列按铁律 11 标「参考」。

**门禁/套件**：全量单测 **1653/1653**；形式门禁 `VerificationForm|SkillGeneralization|DevPlanDocRef` **Failed 0 / Passed 14**；AOT `dotnet publish` rc=0、**IL 警告 0**、体积 **15,438,368 B**（+0.08%）；`bind_evidence --check` **R2E_R2F_EXIT=0**、`decl_sweep --check` **checked=30 drifted=0**；registry rows **223→225**、`updated_round=R510`。

**诚实边界**：① 审批**真机**闭环未测到 —— 动作环声明工具只有 `list_dir/read_file/write_file/run_command`，删除类审批在真机不可达（只有单测闭环 + `unknown_approval` 负控）；② 断线重连时 `task.progress` 补发未测；③ A/B 各 3 轮、单题单模型（before rep2 大面积失败说明管道自身方差大），禁跨轮相减；④ 主线 token 判据（≥30%）**本轮未测**（无 codex 侧对照、不涉 R1 role 挂载轴）；⑤ `SessionBaseline` 前缀 **+74 字符**，既有前缀/缓存 KPI 期望需在下轮刷新。

**下轮候选**：R511-C1 `delete_file` 工具（经审批）+ 审批真机闭环 E2E；C2 断线重连 `task.progress` 补发（按 `step_index` 去重）+ 断言；C3 `restart_recovery`/`incr_concurrent_atomic` 同类 A/B（n≥3）+ 前缀 KPI 期望刷新；C4 全表 `evidence_cmd` 可重放性普查 + 本地 3B 长原文回放。

## R507 补测 · 2026-09-17 · 状态: **完成（交互/人性化 KPI 对照；自检 SELFTEST=OK，NC `detect:NC_DETECTED`）** · 主题: **用户问「有对比过提问数量，人性化，等其他 kpi 么」⇒ 补齐三类 KPI 对照**

**用户问（逐字）**：「有对比过提问数量，人性化，等其他 kpi 么」⇒ 先如实分栏（已对照 / 仅本侧 / 未测），再补器具 + 真读数（只读已落盘件，不重跑被测对象）。

**器具**（`eval/rover/r507pre/`）：`kpi_interaction_r507.py`（`--round` 吃两侧已落盘回复件；`--adapter-dir` 吃冻结适配器快照；`--selftest` 4 用例 + codex-chrome=0 真实数据控制）· `nc_interaction_kpi_r507.py`（正控反空心 + 2 处注入必被抓）· `kpi-interaction.json` · `evidence/interaction-kpi-selftest.json`；登记 `external.contrast-interaction-kpi`（L3，`instruments.json` 31 件）。

**真读数（R502/R503/R504/R505a-c，双侧同式）**
| 面 | 本侧 | codex | 判定 |
|---|---|---|---|
| 对用户提问率（题） | 0.0–12.5%（R504 起 1/11） | 0.0–9.1% | 单轮题集上限 1/题 ⇒ **无区分度** |
| **menu 式问询**（`r458` 焦点令） | **R504–R505c 全 0/11 = 0%** | 9.1–25.0% | **未达，低于外部真值** |
| 人话字/题 | 1029–1332 | 107–193 | 本侧 ≈6–10× |
| 面板行/题 · `@chatbox` 帧 · 产物路径泄漏 | **14.0–15.6 · 12–22 · 11–31** | **0 · 0 · 0** | 可量化人性化缺口 |
| 内部问询（本侧 58 调用） | 4 (6.9%)，占 prompt tok 1.1% | 结构不可对照 | 不打扰用户，非 token 杠杆 |

**覆盖清单**：tokens / 调用数 / 墙钟 / 整题全对 / 可执行前置 = **两侧有**；轮数 / 首通率 / 修复率 / 内部问询 = **仅本侧**（codex `n/a`）；**用户回答频率 = 未测**（须多轮对话题集或真实会话面）⇒ 记 `unreported`。

**基线**：`SELFTEST=OK` · `detect:NC_DETECTED` · `bind_evidence --check` rc=0 ∧ `R2E_R2F_EXIT=0` · `decl_sweep --check` drifted=0（`--apply` 后 `WRITE_READBACK=OK / RE_AUDITED=1`）· 登记行 220 · 未 push（推送暂停令在效）。

## R507pre · 2026-09-17 · 状态: **完成（前置器具 + 真读数复算；L2 自检 9/9）** · 主题: **可验收前置 —— 两侧产出物须「可实际执行且正确」（用户令）**

**用户令（逐字）**：「对比 codex 时，一定要让产出物可实际执行并正确才算可验收对比数据的前置状态」⇒ 落盘 3 处：`docs/reports/iteration-master-plan.md` §0-0 **铁律 11**（宪法级）+ 「三条硬条件」→**四条硬条件**；`docs/external-reference-harness.md` §2 **E7** + **§9**。

**器具**（`eval/rover/r507pre/`）：`exec_precondition.py`（物化 artifact/transcript → `python3 -I -B` 实跑 → 逐条 hidden 用例**整题全对** → `executable_and_correct` + `blocked` 逐条点名；rc `0 可验收 / 1 未可验收 / 3 输入缺失 fail-closed`）· `nc_precond_r507.py`（9 例：正控 / 两次跑逐字节同 / 错值 / 语法错 / 运行即崩 / 死循环 / 非程序题无执行面 / 缺输入 rc=3 / 产物缺失 no_code）· `selfcheck_r507.py`（L2 证据生成 + 真读数复算）· `README.md`。

**真读数复算**（只读仓内已落盘摘要与题集）：R502 两侧 **4/4 执行且正确 ⇒ 可验收**（token −56.3% 成立）；R503 本侧 `vm_run` **8/12**、R504 本侧 `wythoff` **10/13** ⇒ **未可验收**（−33.5% / −37.8% 降级为**参考读数**）。codex 侧产出物为 transcript（须物化才可执行）⇒ 两侧统一到「磁盘上的可执行文件」后独立实跑，codex 侧 R502/R503/R504 = 4/4 · 5/5 · 7/7 全绿。

**基线**：`PRECOND_SELFTEST=OK`（NC 9/9；正控绿 + 注入缺陷必红且点名）· `eval/rover/r507pre/precondition-{r502,r503,r504}.json` · `evidence/precondition-selftest.json`；未 push（推送暂停令在效）。

**诚实边界**：① 复算 = 对**已落盘摘要**的独立重跑，非新一次真机对照；② 只覆盖程序题，见证型数学题无执行面（记 `not-applicable`，仅核正确性）；③ 「整题全对」= 全部 hidden 用例通过，部分对即判**不正确**；④ 判据器内部判分**不算**该前置；⑤ 轮号 = **R507**（器具目录标 `r507pre`，不另占主线编号）；已登记 `external.contrast-exec-precondition`（registry **L4** = 成对正控/负控、注入缺陷必失败且点名）+ `instruments.json`（成对器具 **30** 件）⇒ `bind_evidence --check` **rc=0 / R2E_R2F_EXIT=0**、`decl_sweep --check` **drifted=0**、形式门禁 `VerificationForm` **7/7（Failed 0）**。

## R506 · 2026-09-17 · 状态: **完成（候选④ 闭合 + 常驻守卫）** · 主题: 登记行 `evidence_cmd` 可完整重放

**起因**: R503 起 `r433` 冻结行的 `evidence_cmd` 与它宣称的证据面**不匹配** —— R504 登记为
`PASS_DECLARED_GAP`（9 行只重放出 8 行），缺口未闭合。

| 项 | 读数 | 判据 |
|---|---|---|
| 缺口再诊断 | 缺的不只是 glob: **根本没有 `--compare` 操作数** | 命令操作数级 |
| 工具修 (`--glob` 可重复 + 与 `--run` 并集) | 自检 **24/24 → 28/28**; 旧语义同命令 **rc=2** | PASS |
| 重放闭合 | **9/9 行** + **逐字节等价**(白名单仅墙钟行) `norm_sha12=288c9ff66162` | PASS |
| 负控 (前态臂, 逐字执行前态命令) | 恰好复现缺口: 8 行 / `missing=['probe-m6-agent.json']` | PASS |
| 常驻守卫行 | 登记表 **217→218**; `bind_evidence --check` rc=**0** | PASS |
| 形式门禁 | Failed **0** / Passed **14** | PASS |
| 候选③ 本地引擎退化率 | `MemAvailable 2,696 < 2,800` + 对侧在飞 ⇒ fail-closed | **未测到**（结转） |

**器具自抓 (1 处, 红照原样保留)**: 重放判定器首版以 `(序号, run名)` 作归属键 ⇒ 行集合变化时序号
整体位移，负控臂 8 行**全部**被误报 `missing`（读起来像「缺口 9 行」）⇒ 改为 **run 名作身份键**
（位置量不入键）+ 重名 fail-closed。

**归属三态**: `self` = 上表全部; `foreign` = 兄弟会话在飞的 `eval/rover/r505/`（**未采信、未复核、
未改动**）; `pre_existing` = 9 个既有工作区脏项（未进本轮提交）。

## EXP1-Q42 · 2026-09-17 · 状态: **完成（登记通路复活 + 转正期望时效收口）** · 主题: 尾 LF 闸转正的副作用收口 + exp1q41.* 能力登记

**起因**: EXP1-Q41 把提交面尾 LF 闸由 opt-in **转正为默认开**, 而既有控制件 `selftest_q40_taillf` 的 E5 期望
(「默认档放行坏清单」) 随转正**过期** —— EXP1-Q42 首跑实测 **E5 FAIL / 9-10** (改前真机留档, 非事后追认)。

| 项 | 读数 | 判据 |
|---|---|---|
| 期望时效收口 | E5 → 「默认档拦下」+ 新增 E5b「显式关闸放行」⇒ **11/11 PASS**; 前态负控 **5/5** | PASS |
| 能力登记 | 登记表 **214→217** 行 (`exp1q41.*` ×3, 各带成对控制); `bind_evidence --check` rc=**0** | PASS |
| 形式门禁 | `dotnet test` (VerificationForm\|SkillGeneralization\|DevPlanDocRef): Failed **0** / Passed **14** | PASS |
| 真提交面 (4e50ba8) | `TAIL_LF_GUARD contract=R481-tail-lf targets=2 violations=0 unresolved=0` ∧ `TAIL_LF_GUARD=OK` ⇒ 拦截 **0** | PASS |
| 漂移通知件现场 | 真仓干净态 **0 行**; >0 现场事件**不可达** | 未达 (结转) |

**根因修复 (本轮最承重)**: `bind_evidence.py` 序列化器**硬编码 `indent=1`**, 而登记表自 **R500** 起现盘为 `indent=2`
(r500 写侧 + R502 rebind 沿用) ⇒ `--apply` 恒 `SER_ASSERT=FAIL` / rc=3 ⇒ **能力登记通路死亡** (AN.9 #1 的真实成因)。
修法 = 形态的**唯一权威 = 现盘文件**: `detect_json_form()` 逐字节反解 (indent∈{1,2,4,None} × ensure_ascii∈{False,True}),
命中按现盘形态写回, 反解失败仍 fail-closed。登记表改动量 numstat **80/5** (旧硬编码路径会是 5305 行整份重排)。

**证据件纪律 (自捕)**: `replay_q41_scopeA_classified.json` 含 HEAD 字段 (`head_ct` / `post_contract_window.*`)
⇒ 重跑字节必变 (sha `c6dbd4d1`→`48f65d03`) ⇒ **不得作冻结 pin**; 证据改取**输入不变**归档 + 确定性校验器
(`eval/capability/exp1-q42/verify_replay_archive_q42.py`, V6 = 同输入重算两遍字节相同)。

**诚实边界**: ① H6 的 >0 现场事件真仓不可达 (夹具读数不顶替现场读数 ⇒ 候选结转); ② 形态分叉仍在仓内
(60+ 历史脚本硬编码 `indent=1`, 本轮只修活通路) ⇒ 形态统一须独立预注册轮; ③ 转正后真实复核窗口 n=1; ④ 未 push。

## v0.98.3 · R502 · 2026-09-17 · 状态: **真机首跑完成（对照面 rc=0 全绿）** · 主题: 主线对照读数 —— 随机游戏 × 数学难题 × 程序题 × codex 外部真值

**跑法**: 同窗 / 同冻结题集（probe 口径 sha `18e7c8dddb54e220`, 6 题）/ 同透传 adapter / **同模型**（两侧落盘 `request.upstream_request.model` 均 `deepseek-chat`, 24/24 行一致）/ 同机械判分（`eval/probe/grade.py` 隐藏用例 + 外裁判子进程）。

| 侧 | 整题全对 | 用例 | 调用 | tokens | 墙钟 |
|---|---|---|---|---|---|
| 外部真值 codex-cli | **6/6 = 1.000** | 57/57 | 14 | 113,850 | 97.18 s |
| 本侧 AOT agenthost | **6/6 = 1.000** | 57/57 | 10 | **49,709** | **21.12 s** |

逐题: `life_k 12/12 · topo_min 13/13 · vm_run 12/12 · json_mini 18/18 · witness_sqrt_mod 1/1 · witness_min_counterexample 1/1`（两侧同）。

**判据**: H1 仪器判别力 ✓（oracle 1.0 ∧ `mutation:json_loose` 0.0; 游戏族 `life_wrap` 0 整题全对）· H2 外部真值可用 ✓ · H3 同输入机检 ✓（两侧 == 预注册 sha）· H4 同模型机检 ✓ · H5 读数分列（禁总量断言）✓ ⇒ **rc=0**。

**读数（相对 codex，同质量下）**: tokens **−56.3%**（49,709 vs 113,850）· 调用 **−28.6%**（10 vs 14）· 墙钟 **−78.3%**（21.12 vs 97.18 s）。

**器具缺陷（本轮自捕并已修）**: judge H4 读顶层 `models`（落盘并无该字段）⇒ **假红**；v2 改读 `request.upstream_request.model`（落点由 24 份落盘实测确定）。

**诚实边界**: ① **两侧静态面不同源**（codex 自带 agentic 循环/沙箱/命令执行）⇒ 依 H5 **禁据 token 总量断言优劣**，本节只作对照读数；② n=6 单跑单窗，非独立样本；③ 预注册标签 `deepseek-flash` 为本仓侧标签，供应商侧名 `deepseek-chat`；④ 游戏族 `life_k` 为同轮新增 ⇒ 其跨轮对照为空。

**下轮候选**: ① R501 效果面（t8 guard `reason=question_mark` 修链）；② 题集扩面（更多游戏族/见证族 + 重跑预注册）；③ 证据绑定闸「冻结行 + 器具已改」开放项裁定；④ R492 I7 结构量改写。

## v0.98.2 · R501 · 2026-09-17 · 状态: **裁决完成（结构面 GREEN；效果面不得宣称）** · 主题: 改写族豁免同形四臂复测（真机）

**跑法**: 同 AOT `sha16 62e076eb49e72f62`（IL 0）/ 同网格 / 同窗 02:42–03:15；C(改写关 ×1) + P1/P2/P3(改写开)；起手闸连续 2 次 PASS（2651/2655 MB）；teardown 4/4 clean；MATRIX_RC=0。

**裁决（判据逐字按 `prereg_r501.json`，禁事后改）**: H1p **3/3** ✓（t8 basis = `mechanical:paraphrase→local`，不再是 `gate:skip_rejected_nonack`）· H1n **3/3** ✓（`local_turn_gate_reject=0` ∧ `gate_prefilter_invariant_violation=0` ⇒ **R444 后置否决吞掉改写的问题已除** = R501 修复目标达成）· H2 正控 ✓（C 臂 t8 = `mechanical:nonack→remote`）· H4 ✓（t8 答复 376–517 字、非复读、degrade 均带 reason）⇒ **VERDICT=GREEN（结构面）**。

**效果面（不得宣称）**: 3/3 P 臂 t8 均走 **degrade 支** —— 本地改写被 **paraphrase guard 拒收（reason=`question_mark`）** 后降级远端 ⇒ t8 仍有 1 次远端调用 ⇒ 按 H3 **禁宣称本地生成/改写收益**（残留缺口从「后置否决」下移到「guard 拒收」）。

**用量（单源 = `judge_paraphrase_r499.py` 中继 usage 真值）**: C 12 调用/77,222 tok；P1 13/69,049（−10.58%）；P2 12/75,655（−2.03%）；P3 13/68,445（−11.37%）；均值 **−7.99%**；`empty_body` 各 1。n=3 重复跑 ⇒ 组件级读数，**不用于宣称 ≥30% 主线达标**。

**质量守卫（如实记 red，不修判据）**: judge `J2e` 在 P1/P2 红 —— t8 答复引入源文没有的标识符（`.sln` / `csproj` / `dotnet build` 等）；P3 绿。两臂该答复来自**远端 degrade 支**。

**裁决器修复（本轮自捕, 读写契约不一致）**: `verdict_r501.py` v2 —— ① 臂写侧 `turns-*.jsonl` 是单对象 pretty JSON（原按逐行解析 ⇒ JSONDecodeError）；② `local_turn_gate` 行**无** top-level `msg_sha16`（原按该字段匹配 ⇒ t8rows 恒空 ⇒ H1p/H2 **假红**），改用「第 8 条 gate 行」+ `degrade_rows.kv.msg_sha16 == sha16(t8)` 交叉校验（不一致 ⇒ rc=2 fail-closed）。

**诚实边界**: 跨轮禁相减（R500 的 C 仅作方向对照）；R501 的 C 与 R502 的对照窗不同，禁混算。

## v0.98.1 · R502 · 2026-09-17 · 状态: 铺件完成（预注册先于首跑 + 负控全绿；**真机首跑已完成 ⇒ 见 v0.98.3**） · 主题: **主线执行面 = 开发任务对照套件（codex-cli 外部真值 × 机械判分）**

**背景（主线口径 · 承 v0.98.0）**: 主线 = 用「随机程序 / 数学难题 / 游戏」真实开发任务与外部真值（codex-cli，同一真实模型）同环境·同输入对照，对本项目做质量自检。本节落的是**可复跑的对照执行面**，不是一次性读数。

**完成记录**
1. 外部真值工具面持久化: `@openai/codex@0.154.0` 装到 `~/.agentframework/tools/codex-env`（与 R455 同版 ⇒ 跨轮同版可复现；旧 `/tmp/codexenv` 不可托付）。
2. 冻结题集 v2: `eval/rover/r502/taskset-r502.json`（**6 题** = 4 程序族 `life_k`(**游戏族**)/`topo_min`/`vm_run`/`json_mini` + 2 见证型数学族 `witness_sqrt_mod`/`witness_min_counterexample`，seed 20260917）；**probe 口径 sha `18e7c8dddb54e220`**；oracle 正控 **57/57 = 1.0**；构造法 = **逐族定向 dump 后机合并**（禁抽样碰运气；合并前断言旧 tid 不出现在字段内）。
3. 两侧同面: 本侧 = AOT `agenthost`（probe `agent` 解法）；外部 = codex-cli（probe `command:` 解法，stdin 题面 → stdout 回复）；两侧同经 R455 透传 adapter（**同一真实模型**）⇒ usage 真值同源。
4. 判分 = `eval/probe/grade.py`（隐藏用例 + 外裁判子进程）—— **同一判分器**，禁模型裁判。
5. **预注册先于首跑**: `prereg_r502.json`（**9 件**哈希机取 + 6 条判据 + 4 条诚实边界；题集元信息/正控基线也机取，禁硬编码）；`--check` 三态 rc 0/1/3。
6. **首跑前负控全绿**（本地，不吃真机窗）: 程序面 oracle 1/1 ∧ `mutation:json_loose` 0/1；**游戏族** oracle 1/1 ∧ `mutation:life_wrap` 0 整题全对（3 题实测 16/36 用例 ⇒ 变异确实被隐藏用例抓到）；缺侧 judge rc=3；预注册 uniform/drift/missing/restored = 0/1/3/0；solver `--selftest`/`--dry-run` rc=0；生成器 `tasks.py --selftest` **47/47**。
6b. **游戏族补入（主线钦定「随机游戏」面）**: `eval/probe/tasks.py` 新增 `life_k`（Conway 生命游戏第 k 代；8 邻域/同时更新/**网格外视为死**；隐藏用例含「边界不环绕」判别 —— 1×3 的 `###` 一代后应为 `.#.`）；`run_probe.py` 增 `REF_SRC["life_k"]` + 族变异 `("life_k","life_wrap")`（环绕边界 ⇒ 判别力负控）。
7. 文档入册: `docs/external-reference-harness.md` **§7**（主线常态执行面）+ `eval/rover/r502/README.md`（由 §7 机械派生，单一真源）。
8. 提交: 显式路径 + `STAGE_GUARD` + 越界白名单（未 push，PUSH_PAUSED 在效）。

**基线（器具自检，非对照读数）**: 题集 oracle **57/57 = 1.0**（6 族全覆盖）；`mutation:json_loose` 整题全对 0/1；`mutation:life_wrap`（游戏族）整题全对 0（用例级 16/36）。

**器具缺陷（本轮自捕并已修）**: ① **NC `EXIT` trap 覆盖汇总写回** —— `restore()` 在脚本退出时把 `keep.json` 拷回 `prereg_r502.json`，导致 `checks_prefirstrun` 写回被静默抹掉（症状: NC 打印 rec 且总判 OK，但 prereg 里无该字段）。修法 = NC3 复原后 `rm -f "$KEEP"` 关闭 trap 复原；修后复跑：`checks_prefirstrun` 落盘可见（NC1/NC1b/NC2..NC5 全在）。② **证据绑定闸对「已冻结行 + 器具已改」结构性不可满足（未修，记开放项）**: 改 `eval/probe/tasks.py` 后 `probe.randomized-selfcheck`（frozen/artifact，`instrument_sha12=80ba09e8bd50`）被判 VIOLATION（现盘 `32815065ff7a`）；hook 给的处置 `bind_evidence --only <id> --round <轮号> --apply` **实测无效** —— ①真表上 `SER_ASSERT=FAIL`（本仓登记表以 `indent=2` 落盘，工具序列化器为 `indent=1`）；②**在 indent=1 的 scratch 副本上仍判 VIOLATION**（该工具只刷 `audited_by_round`，不重钉 frozen 行的 `instrument_sha12`）⇒ 与格式无关，是**闸规则与冻结语义冲突**。本轮处置 = 提交时用 hook 自带的 `AGENTFRAMEWORK_EVIDENCE_CHECK=0` **定向让行**并全文留痕（**不声称任何被判据覆盖的绿灯**；登记的既有冻结行字节与哈希一字未动）；开放项 = 需一次性裁定「器具已改时冻结行的重审语义（改判据 or 重钉 or 新建行）」。

**诚实边界**: ① **真机首跑未做** —— `MemAvailable` 实测 1,283 MB 且 R501 真机 4 臂在飞 ⇒ 让行；本节**不得**被引用为「本 agent vs codex」的任何结论；② codex 沙箱面不对等（本机 `bwrap` 不可用 ⇒ `--dangerously-bypass-approvals-and-sandbox`）；③ 两侧静态面不同源 ⇒ 禁据 token 总量断言优劣（H5）；④ 游戏族**已补**（`life_k`）⇒ 主线「随机游戏」面已可覆盖，但**真机读数仍缺**；⑤ 补族后预注册 v2 仍属**首跑前**生成（未发生任何真机对照跑）。

**下轮候选**: ① **R502 真机首跑**（R501 收口后同窗两侧 + `judge_contrast_r502.py` 出读数；禁与真机测量并发）；② R501 裁决与代码面提交；③ R492 I7 结构量改写；④ 题集扩面（补 `witness` 面/更多族并重跑预注册）。

## v0.98.0 · R501 · 2026-09-17 · 状态: 已完成（文档面；真机裁决另轮） · 主题: **主线定义更正（用户钦定）+ 铁律 10 入册（宪法级）**

- 用户逐字（2026-09-17）: 「主线不是让你用【随机游戏或数学难题开发】对比codex开进行本项目质量自检么」+「请更正主线并加入铁律」。
- 更正后主线（宪法级，`iteration-master-plan.md` §0-0 铁律 10）: **用「随机游戏 / 数学难题 / 程序题」的真实开发任务，与外部真值（codex-cli，同一真实模型）在「同环境·同输入·同模型」下对照 ⇒ 对本项目做质量自检**。
- 口径分层: 主线 = **方法**（外部对照自检）；R413「一轮任务总 token ↓≥30%（主因 = 不必要的远端 LLM API 请求少了）」= 该主线的**判据之一**，不再等同主线（更正前口径错位: 判据当主线 ⇒ 自我窄化）。
- 三条硬条件: ① 同环境同输入（两侧夹具逐字节同，md5 一致才许开跑）② 输入须逐模块可测 ③ 机械判分（禁模型裁判 / 禁事后补记）；「只读本仓内部读数/自报」= 封闭系统自证 ⇒ 记为**未自检**。
- 更正载体（4 处，全部落盘）: ① `docs/reports/iteration-master-plan.md` §0-0 新增铁律 10 ② `docs/external-reference-harness.md` §1 标注「本文档 = 主线方法的常态载体」 ③ `docs/reports/dynamic-telemetry-eval-rollback-strategy.md` §7 最新状态改为「主线 = 外部对照自检；R413 KPI = 判据之一」 ④ cron 两作业（`9a97763d5fcd` 30m 主线段改写 + 改名；`b15eb2f40a69` 60m 插入主线定义段）+ `MEMORY.md` 主线铁律条。
- 诚实边界: 本轮**只改口径与文档**，未新增真机读数；R501（本地改写通道豁免复测，4 臂）**裁决未出**，其结论只在上述主线的方法学下解释（同环境同输入对照的一环，不等于主线已验收）。
- 基线: 全量测试 1633/1633（R501 src 改动后）；AOT `/tmp/pub_r501/agenthost` IL 0 / sha16 `62e076eb49e72f62`。

## v0.97.0 · R481 · 2026-09-16 · 状态: 进行中（D9 已验收：测试面 14/14；【探索】R481-A 的 G1/G3/G4 未达） · 主题: recall 模块工程收口 + 【探索】精度判据锁定（承 v0.96.0）

> 版本区间说明: 本文档上一节停在 **v0.81.0 · R462**；**R463–R478** 的逐轮记录见 `docs/reports/iteration-master-plan.md` 的「R441–R478 轮次索引」段（机取自 `docs/verification-registry.json`，含 38 个轮号）与 `docs/plans/v0.9*.md` 各轮计划，本文件不重写历史。

- **R479（已收口并提交 `058bc77` + `e157deb`）**：Responses 真实 I/O 格式 + 内部精准语义单出口 + 工具声明面单一事实源。真读数：形式面 **1490/1490**；形式门 **10/10 × 3**；AOT sha16 `c8974f6b34dcc7b3`；台账 146→149 / 46→47 幂等。
- **R480（在飞，未提交）**：独立工程 `src/agent.recall`（**不并入 `agent.sln`**，成熟后合回），15 个文件落盘（binary 格式 / LEB128 varint / postings 在线 delta + 每 128 文档 block-max / 词表二级跳表 / BM25 + WAND / 目录 mtime 剪枝 + 流式归并指纹 / 只重建脏文档 + tombstone），库编译 `rc=0 / 0 warning / 0 error`。
- **R480-C（结论已落盘，`docs/reports/r480c-summary-vs-classification.md`）**：**摘要→分类当过滤器路线证伪** —— 一级分类当过滤器漏 **81.83%**（灾难）、二级分类漏 **5.83%**（不可恢复）；分类聚焦收益≈0（rankP50 92→90、r@10 36.67%→36.50%）；主凶是**候选截断**（top-10 漏 **63.33%**）。裁定：分类只能当排序特征/剪枝（**永不排除**），截断必须可回退；规模 5,747 文件 / 98 MB / 1,456 叶子目录 / 600 查询 / 19.1 s。
- **R481-A（基线已取，`eval/recall/prereg_r481a.json` 先于首跑落盘）**：【探索】跨文件/跨 URL 精度基线 —— 解析率 **0.8508**（目标 ≥0.90 ❌）、悬空 **0.1492** ✅、相对引用落地 **0.2718 = 309 条** ❌、地址覆盖 **p50=0 / 76.11% 文件零地址** ❌、跨 URL **2,720 条 = unreported**。规模 6,647 文件 / 20,155 条自带地址。
- **R481-B（统计结案，用户授权「按统计学规律则优」）**：点号是否算词字符 —— 2,500 真实文件 × 300 真实查询（stem / 全名 / 相对路径 各 1/3），hit@5 差 **+0.67 pt**（p=0.856 不显著），而不算点号侧查询词数 **−16.05%**、postings **−0.254%** ⇒ 取成本更低者：**点号不算词字符**（`RecallTokenizer.cs:31` `WordSymbols="_/+#"`）。
- **R481-C（本轮，测试面收口）**：`agent.recall.tests` **2/13 → 12/13**；`OutOfMemoryException` **16 → 0**；用例耗时 **2m12s → 391 ms**；库 `rc=0 / 0 warning`。7 处根因全为**读写契约不一致 / 越界 / 未 fail-closed**（F1 `RecallIndexMeta.Read` varint 错位 ⇒ OOM；F2 `RecallSegmentMeta.Read` 同类；F3 `RecallPostings.Flush` 记词表内偏移；F4 `RecallLinks.Read` 游标未推进；F5 `RecallUpdater` 首建硬 `Open`；F6 孤立 CJK 段零 token；F7 `RecallFormat.DocLength` lens 表头 12 B 被按 4 B 读 ⇒ BM25 分数漂移 `3.4674924292638662 vs 4.005845527737886`，修后与独立暴力打分逐位一致），**无一处改断言凑绿**。
- **R481-D（本轮，D9 收口）**：`agent.recall.tests` **12/13 → 14/14**（Failed 0 / Skipped 0 / trx 结果行 14）。根因(承 R481-C 定位)：目录剪枝条件 `dir.mtime <= 上次 stamp` 对**纯内容改写**不可见(改写文件不改父目录 mtime) ⇒ 整目录被剪 ⇒ 文件级 `(size, mtime)` 比对根本没发生。修法 = **交替核验**：指纹头 stamp 低位记「上轮是否剪枝」，上轮剪过的目录本轮**强制核验**(readdir + stat，不读内容)，idle 轮仍剪枝；纯内容改写最多滞后 1 轮被捕获。语义变化单列：核验轮 `DirsPruned == 0` ∧ `VerifiedAllDirs == true`(不冒充「无变化」)。新增回归用例刻意用**等字节长度**改写(size 不变) ⇒ 逼出「文件级比对必须真的发生」，并锁「核验轮 DirsPruned 恒 0」「下一轮恢复剪枝」两条。器具 `eval/recall/r481/check_r481d9.py` 判 `verdict=PASS`：C1 源码派生(读写契约成对) + C2 真跑读数(trx 14 行) + C3 语义锁存 + 变异负控 **3/3**(NC1 反转剪枝门 / NC2 删 stamp 左移 / NC3 删标志位解码 ⇒ 全部翻红)。
- **R481-E（本侧，独立复核 + 文档对账）**：D9 由 cron 兄弟会话（`cron:9a97763d5fcd`，07:42–07:45）实施；本侧**不采信对侧自述**，逐项自跑复核 —— `dotnet test src/agent.recall.tests` ⇒ **rc=0 / Passed 14 / Failed 0 / 576 ms**；`dotnet build src/agent.recall -c Release` ⇒ **rc=0 / 0 warning / 0 error**；`python3 eval/recall/r481/check_r481d9.py` ⇒ **rc=0 / verdict=PASS**。文档对账 4 处：本文件标题行去重（对侧写入时残留重复 `主题:` 片段）、`docs/plans/v0.97.0-r481-consolidation.md` 状态行/代码事实/A1 验收更新为 **14/14**、`docs/reports/iteration-master-plan.md` 的 R481 机取索引段由**空表（轮号 [] / rows=149）**修为实表（**轮号 ['R481'] / rows=150 / updated_round=R481**，`master_plan_round_index.py R481` rc=0 / 336 B 直接产出）。
- **基线(修后)**：`agent.recall.tests` **Failed 0 / Passed 14 / Total 14**（rc=0，`Duration 949 ms`，`Skipped 0`；R481-C 前为 **Failed 1 / Passed 12 / Total 13**）；库 `dotnet build src/agent.recall -c Release` = `0 warning / 0 error`。
- **R481-E 增量（G2 产品面，本侧实施）**：`RecallLinks.ResolveReferrerRelative`（纯字符串代数）+ `RecallIndexWriter.cs:70` 传 `doc.Path` ⇒ `./`、`../` 显式相对引用按**引用方目录**解析为根相对；**越根 fail-closed 原值返回**；**根相对（主力通路 root-fallback 16,965/20,155）与绝对 URL 一律不改写**。新增用例 `Relative_References_Resolve_Against_Referrer_Directory`（含越根负例）⇒ **Failed 0 / Passed 15 / Total 15 / rc=0 / 455 ms**（14 项零回归）。**诚实边界**：G3 = 0.2718 是**语料侧 Python 代理面**读数，产品面本改动**尚未在语料上重测** ⇒ 不宣称 G3/G1 达标。
- **R481-F（本轮，语料侧重测，承计划 §7）**：R481-A 的端口是**手写规则**（后缀白名单 + 裸名计入相对档 + `lstrip` 兜底），与产品已静默漂移 ⇒ 重建**源码派生端口** `eval/recall/links_port_r482.py`（7 组规则常量正则派生、任一派生失败 rc=3 弃权；期望值取产品自身断言的用例；6 条规则变异 **6/6** 被抓；唯一变量 = 抽取规则）。新口径真读数（6,658 文件 / `files_sha16 1000893f7926c08c`）：候选 **76,404**、解析率 **0.1450 ❌**、悬空 **0.8550 ❌**、显式相对引用 **660 条 → 落地 72 = 0.1091 ❌**、地址覆盖 **p50=5 ✅**、越根 fail-closed **2** 条、绝对路径形态 **7,462** 条单列。**按通路分解**：markdown **81.25%** 落地 / 裸 URL 全 `unreported` / 相对地址串 **14.43%**（悬空 64,004 = 99.98%）⇒ 判据在全候选档上**结构不可达**，相对引用改写可达面仅 **0.88%**（天花板 ≤ +0.88 pt）。旧端口同批对照 0.8504 / 0.1496 / 0.2650，**口径已变更 ⇒ 跨轮不可比**。台账 `docs/reports/r480-recall-test-ledger.md` R481-F 段。
- **R481-G（本侧，语料钉 + 分档口径预注册）**：① 独立复核 R481-F ⇒ `links_port_r482.py --selftest` **rc=0**（6/6 变异被抓）、`--out` **rc=0**，读数同向同量级（G1 0.1449 / G2 0.8551 / G3 0.1086 / p50=5 达标）；`old_arm.match=false` 已自标**不可比（语料漂移）**。② **新发现（机制缺口）**：器具只绑定 `corpus.files_sha16`，不绑 commit/工作树 ⇒ 实测 **3 个不同语料钉**（`251b1c166eca7dbe`/6659、`1000893f7926c08c`/6658、`737b2cca752d55bc`/6683，`head=ccb132b`、`dirty=37`），而**规则钉恒定**（`9e9104ca601f8849`）⇒ R481-F 的「两次独立运行逐字节相同」**只在同一语料成立**，漂移无报警。③ 器具 `eval/recall/r481/check_corpus_pin.py`（三态 fail-closed：UNIFORM rc=0 / DRIFT rc=1 / MISSING rc=3），负控 N1/N2/N3 = **rc=3 / rc=1 / rc=0** 全中。④ 预注册 `eval/recall/prereg_r481g.json`：语料钉三元组 + 可比性规则 + **分档判据**（markdown ≥0.90、root_rel ≥0.90、explicit_rel ≥0.85、slash_token 不设门槛、url `unreported`）⇒ 全局 `resolved_rate`/`dangling_rate` 门槛在含 slash token 的候选面上**结构不可达**，判据收窄。**诚实边界**：分档读数**未取得**（器具需加 `by_subband`）；`files_sha16` 无文件清单 ⇒ 漂移**可判不可归因**；Python 代理面，不测产品面延迟/实现；未 push。
- **诚实边界**：`agent.recall` **尚未并入 `agent.host`** ⇒ 本面无 AOT 重发布验证；`src/agent.recall*/` 仍 **untracked**；全程**未 push**（`PUSH_PAUSED`，ahead 196）；R480-C / R481-A 均为 **Python 代理面**，不测产品面延迟/实现；**LLM 生成摘要臂与 1e5 文件档均未测**；跨 URL 一律 `unreported` 不冒充 0。
- **下轮候选**：① 内容级哈希兜底（`VerifyMode.Hash` 或周期全量核验：D9 只保证「最多滞后 1 轮」，**不保证**任意改写当轮可见）② 相对地址按引用方目录解析 ⇒ G3 0.2718↑、G1 ≥0.90 ③ 判据锁进 `prereg_r481a.json` ④ 1e5 规模臂 ⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）—— 注意：recall 模块**尚未入链**，R413 主线「用户一轮 tasks tokens −30%」在本面无贡献（本面只做模块正确性收口，不冒充主线 KPI）。

## v0.81.0 · R462 · 2026-09-15 · 状态: 已完成 · 主题: 召回-现实一致性闸 + 语言无关召回探针（+ r1 权重档位探针）

- **起因（承 R461 实发证据）**：① 召回/记忆块里引用的上一会话事实被当成本轮真值 —— T5 宣称 `stats.txt 已写入 chars=15` 而工作区**无该文件**（磁盘 0 B，真值 14）⇒ 产物 3/4；② `ContextAssembler.RecallFromWorkspaceAsync` 用**硬编码后缀白名单**（源码逐字列语言后缀）过滤召回文件，违反 R447 用户令「管道内一律标通用代码逻辑」。
- **输出效果（E2E 同夹具/同 7 轮/同适配器，唯一差异 = 二进制；判据预注册 4 项）**：P1 召回-现实一致性可见 **11 个实发消息带 `[核验✗ …]`**（`recall_stale_refs` 含 `report.md`）✅；P2 语言无关召回：`[工作区文件 logic.unit]` **进面**、`[工作区文件 blob.bin]` **不进面** ✅；P3 只打假（召回片段内 0 处 `[核验✓` ⇒ 一致时零字节）✅；P4 无回归（7 轮 ok、四产物正确、回复面 0 处契约声明）✅ ⇒ **E2E PASS 4/4**。负控（同判据跑 R461 实发面）P1/P2 = **false** ⇒ 判据有判别力。
- **机制修复（5 项，非关键词/提示词补丁）**：① 新增 `src/agent.core/core/RecallRealityGate.cs` —— 逐子句抽**路径样 token**（结构判定、零后缀白名单）→ 用**文件系统**裁决并追加 `[核验✓ 现存 N B]`/`[核验✗ 当前不存在该文件]`/`[核验✗ 越界路径…]`；fail-safe、幂等、越界不探测、`failOnly` 一致时零字节；② 闸接入**工具回灌面**（`ActionLoop` 回灌前核验；`IActionPort` 增 `WorkspaceRoot` 端口，默认 null ⇒ fail-safe）；③ 召回片段同接 fail-only 核验；④ 删后缀白名单 ⇒ `WorkspaceTextProbe` 结构+内容探针（空/NUL/二进制 ⇒ 弃，后缀集只在 `AGENTFRAMEWORK_TEXT_SUFFIX_ALLOWLIST` 显式配置时生效）；⑤ 语言标签集外置为数据 `config/base/language-tags.txt`（判定器/机检只读数据，源码零硬编码）。
- **判据修订留档（不粉饰）**：v1/v2/v3 的 false 全属**器具/口径缺陷**（召回窗口被运行期 `data/` 占满；P4 误把 system prompt 的契约说明当成「上前台」；P2 被 `list_dir` 工具结果污染；P1 通道未覆盖）⇒ 逐条留档 + 修机制；**P1 判据从未放宽**。
- **r1 权重档位探针（用户问「现役 r1 参数权重够不够」）**：语料 = **产品实发**门判 prompt 逐位 28 条（14 负类真实驱动消息 / 14 正类 Ack），oracle = 网格 `expected[]`（机械，与 r1 无关）；调用面与产品一致（`/completion`、`samplers=[temperature]`、temp=0）。基线 **1.5B-Q4_K_M：准确率 0.321、假跳率 0.929（13/14 真实驱动消息被判「该跳」）、漏跳率 0.357、解析失败 1** ⇒ 该权重在判别面**不可承重**（现状靠机械守卫兜住，R452 `skip_rejected_nonack`）；四档对照臂（1.5B-Q8 / QwenPaw-Flash-2B-Q4 / 3B-Q4 / 3B-Q5）读数见 `docs/reports/recall-reality-gate-r462.md`。
- **验证**：单测 `RecallRealityGateTests`+`ActionLoopTests` **32/32**（构建 0 Error）；AOT `/tmp/pub_r462/agenthost`（15,322,688 B）`env -i` 自启 rc=0。**未 push（推送暂停令）。**

## v0.80.0 · R461 · 2026-09-15 · 状态: 已完成 · 主题: 契约声明**不上前台** + 零字节产物可见 + 每轮注入预算收口

- **用户令（逐字，承 R460）**：「r458回复要精炼，并且后续选择 给出 menu问询了么」+「而且命中率和tokens都不达标」。
- **输出效果（同夹具/同 6 轮/同模型，唯一差异 = 二进制；夹具两侧 md5 同值）**：前台契约声明行 **3 处（37/59/33 字符）→ 0**（负控：同判据跑 R460 落盘回复 ⇒ 命中 3 处，有判别力）；T5 承接回复 241 → 160 → **152 字**；T6 146 → **118 字**（无内部术语）；承接块 **288 → 164 字**；菜单 **3 项（①②③）** 且门 `Choices` 与兜底反问同源；稳态命中 **90.2% → 91.2%**、稳态 miss 均价 **301.9 → 274.9 tok（−9.0%）**。
- **诚实边界（不粉饰）**：① **tokens KPI 未达标**（prompt ∑ **46,616** vs R458 54,927 = −15.1%，目标 ≥30%；R460 曾 −27.4%）；根因 = **调用数方差**（17 / 13 / **15** 次），非前缀长度。② **命中 97% 红线未达标**：算术条件机检 ⇒ 平均前缀 3,118 tok 时需**每轮新内容 ≤93.5 tok**，实测 ≈275 tok（召回块+记忆块+承接块），设计上互斥 ⇒ 唯一杠杆 = 按需注入（R462 靶点）。③ 产物 **3/4**：`stats.txt` 本轮**完全不存在**，模型（T5）却宣称 `chars=15` —— 机检 `recall_stale_refs=[stats.txt]`，即**召回块引用的上一会话事实被当成本轮真值**（R462 靶点，正对用户钦定「用 r1 判别真假信息」）。④ P2「零字节产物可见」本轮**空判**（0 B 文件未进 top-3 块），不得当作通过。
- **机制修复（5 项，均有单测）**：`FormalPromptContract.SplitFacing`（围栏/裸块/`no_formal:` 行剥离到验证面 + 遥测 `contract_declaration_hidden`，剥离为空 fail-safe 返回原文）；记忆写入同剥离（召回块不再带 `no_formal:`）；0 字节产物标 `(空)`（原静默省略）；`ForecastRecord.HeaderTaskPreviewChars=24`（完整文本仍在任务方向里）；每轮预算 `MemorySourceBudgetTokens` 500→**120**、`SessionMemory` 默认 1000→**400**、【已完成】4→**2** 条 + 回归锁。
- **验证**：全量单测 **1357/1357**；形式门禁 9/9（真名 + 断言执行数 > 0）；AOT 重发布 `env -i` 起 rc=0（15,314,448 B）；registry rows **104** / `updated_round=R461`。

## v0.79.0 · R460 · 2026-09-15 · 状态: 已完成 · 主题: 承接轮**精炼** + 菜单**单源** + 命中率/token 归因

- **用户令（逐字）**：「r458回复要精炼，并且后续选择 给出 menu问询了么」+「而且命中率和tokens都不达标」。
- **输出效果（同夹具/同 6 轮/同模型，唯一差异 = 二进制）**：T5 回复 **241 → 160 字（−33.6%）**；承接注入块 **288 → 163 字（−43.6%）**；T6 146 → 123 字（剥离合同标记后 **87 字**）；**菜单问询 = 给了**（门 `ask` 事件 T5 触发，`Choices` = 3 真实产物名 + 「另有新任务」；回复自带 3 项编号菜单 ①②③，首项接地真实产物）；**空态通用示例菜单（搜索资料/写文档/…）已删除**。
- **tokens**：prompt ∑ **54,927 → 39,863（−27.4%）**，调用 **17 → 13（= codex 同数）**，每调用 prompt 均价 3,231 → 3,066。**命中率未达标**：总 90.4% → 85.1%、稳态 90.2%（miss 均价 301.9 tok/call，R458 310、codex 236）—— 根因 = 前缀被主动压小（分母 3,066）而新内容未同比压缩；实发全量文本归因显示 **`[SessionMemory]` 注入块逐轮膨胀 308→417→613→836 字符**，是 miss 主质量。
- **机制（禁关键字/提示词补丁）**：① `MaxArtifacts` 8 → 3 + 紧凑两行块（`MaxBlockChars=200`，截断诚实标注保留）；② 新增 `BuildMenu`/`BuildAsk`，`ComposeFallback` 改调 `BuildAsk` ⇒ **门问句与兜底反问同源**（菜单必现，机检 `Assert.Equal(BuildMenu, Choices)`）；③ 空态不再给通用示例枚举；④ 人话承接句 78 → ≤48 字（`MaxNoticeChars`）；⑤ 器具面新增 `ADAPTER_DUMP_FULL=1`（实发全量消息落盘，禁重建）。
- **本跑暴露的真实缺陷（R461 靶点）**：① **合同标记上前台** —— T4 裸 `clickproof/premise/goal` 5 行、T6 `no_formal: …` 1 行；② **空产物未接地 + 宣称即伪造** —— T4 无任何 tool_call 却回复「stats.txt 已写入 chars=15」（磁盘 0 B、真值 14），承接块过滤 0 B 文件使模型改用记忆假值 ⇒ 产物 3/4。
- **交付**：`src/agent/context/ContinuationBrief.cs`、`src/agent/registry/EvidenceGate.cs`、`src/agent/intent/PlanResumeService.cs`、`src/agent/IndustrialAgentV2.cs`、`src/agent.tests/ContinuationBriefTests.cs`（**16/16 绿**）、`eval/rover/r460/*`、`docs/plans/v0.79.0-r460-brevity-menu-cache.md`、`docs/reports/brevity-menu-cache-r460.md`；registry `r460.brevity-menu-cache`（L2，5 条负控）。未 push。

## v0.78.0 · R458 · 2026-09-15 · 状态: 已完成 · 主题: 承接轮**人性化**（像人一样先承接事实、再反问「继续什么」）

- **用户令（逐字）**：「…得做一些人性化的补充，比如t5感觉codex更胜一筹，比如一个人对另一个人突然说一句，"继续"，另一个人不明所以，肯定就会反问"继续什么"」。
- **输出效果（同夹具/同 6 轮/同模型，唯一差异 = 二进制）**：T5「继续」R456「『继续』没有指向明确动作」→ R457 承接 1 项 → **R458 逐项承接 4 项真实产物 + 「继续什么」反问 + 3 个具体可选项**（`count.txt=4`、`merged.txt=ALPHA/BETA/GAMMA`、`stats.txt=chars=14`、`notes.md`；固定示例菜单 `(如: 搜索/写文档…)` 消失）；T6 内部术语 **3 行 → 0 行**（一句人话 + 干净答案）；产物 **4/4 不回退**，磁盘伪造 0。
- **机制（禁关键字/提示词补丁）**：① 判定面复用意图层既有分支**且与门同判据**（弱意图 且 置信 < 0.60）；② 接地面扫描工作区**真实**产物（名=首行 (字节)，噪声目录排除、有界、截断如实标注「共 11 项, 只列最近 8 项」）→ 本轮注入 `[承接状态 v1]`；③ 门问句由真实产物接地（无产物则明确写「还没有」且列不出文件名）；④ 收口面 fail-closed（回复既无问句又不含真实产物名 ⇒ 链自身用同一批事实组装反问）；⑤ 告知面把「落不到槽位」的内部判定改为一句人话（内部术语/理由只进遥测）。
- **读数**：承接块遥测 1 次（仅 T5，state=grounded）、收口闸 1/1 true、调用 17（R457 15 / codex 冻结 13）、工具执行 12、缓存 90.4%。
- **交付**：`src/agent/context/ContinuationBrief.cs`（新）、`src/agent/registry/EvidenceGate.cs`、`src/agent/intent/PlanResumeService.cs`、`src/agent/IndustrialAgentV2.cs`、`src/agent.tests/ContinuationBriefTests.cs`（15/15 绿）、`eval/rover/r458/*`、`docs/plans/v0.78.0-r458-humanized-continuation.md`、`docs/reports/humanized-continuation-r458.md`；registry `r458.humanized-continuation`（L2，5 条负控）。
- **诚实边界**：调用数 17 > 15（模型自身多用工具，非承接机制成本；同输入跨轮波动 7→9→15→17，单轮不作趋势）；run1 曾误判「当前目录下有几个 .py 文件？」为承接轮并污染回复 ⇒ 已修 + 机检固化；构建脚本曾因无 `set -e` + `--no-build` 出现一次假绿（陈旧二进制 13/13 → 修后 15/15）；未 push。

## v0.77.0 · R457 · 2026-09-15 · 状态: 已完成 · 主题: 动作环**效果收口**（2/4 → 4/4）+ 三缺口机制修复 + 器具对称

- **产物（同夹具/同 6 轮/同模型 deepseek-flash，逐字节比对）**：R455 0/4 → R456 2/4 → **R457 4/4**（`count.txt=4`、`merged.txt=ALPHA/BETA/GAMMA`、`stats.txt=chars=14`、`first.txt=R455 fixture note`）；codex 冻结 4/4。
- **三缺口（机制修复，非关键字补丁）**：① 断言不执行 → 工具结果尾部**执行台账**（`[本轮已执行]`），命中 8 个实发请求，stats.txt 落地且值正确（R456 为口算 15+无文件）；② 吞并轮 → 检查点作废后**同轮转正常任务路径**（`AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH` 默认 on），first.txt 落地；③ 缺 key 静默 → **可见失败**（`ContentIsUserFacing` + `model_unavailable` 遥测），真机负控 `len 0 → 83`，`empty_reply:false`；附带修遥测 JSONL BOM。
- **器具对称**：我方 `tool_calls` 落盘（15/15 有值）、审计 `args_head` 命令原文、适配器 `prompt_sha8`+`tail_messages`；夹具两侧 md5 同 `fe1f5530446bd4ceb8be1b944c8ec005`。
- **读数**：审计执行 4→8；调用 9→15（真干活回灌成本）；prompt ∑31,537→53,163；缓存总口径 84.8%→**89.8%**（稳态 91.8%）。
- **交付**：`src/agent.modelqueue/ActionLoop.cs`、`src/agent/action/WorkspaceActionPort.cs`、`src/agent/IndustrialAgentV2.cs`、`src/agent.modelqueue/ModelQueueRouter.cs`、`src/agent.config/AgentTelemetry.cs`、`src/agent.tests/ActionLoopTests.cs`（52/52 绿）、`eval/rover/r457/*`、`docs/plans/v0.77.0-r457-effect-closure.md`、`docs/reports/effect-closure-r457.md`；registry `r457.effect-closure`（L3，含 5 条负控）。
- **诚实边界**：调用数上升属真执行成本；冷启动首调用读数受 provider 跨运行前缀缓存影响不可跨轮直接比；未 push。

## v0.66.0 · R446 · 2026-09-15 · 状态: 已完成 · 主题: 判官侧**确定性根因(H2)** + 消息面 0-token 结算**负结论** + 判官 prompt 瘦身**未过等价性** + 器具面并轨

- **确定性（真机产品路径, 26 样本）**: 3×12 轮 + 1×24 轮同消息网格 ⇒ 判官字母全同、`ev/new/gen`=215/215/92 全同
  ⇒ **判官路径确定**; 归档「同消息三态并存」= `上一轮` 文本差异（判决 = f(msg, prev)）, 非路径非确定。
  加长版 `verdict-JDET24-s1.json` 四条判据全绿; 12 轮版按预注册门槛**如实记 INVALID_PREMISE**（未改阈值）。
- **候选②「0-token 结算」负结论**: v1（`好，/行，/可以，`+contains）**误赏 9 行**; v2 精确串白名单按 run 划分
  = **方法缺陷自纠**（按 run 划分 ≠ 按拟合单元划分 ⇒ 同消息跨半泄漏）。
- **候选①「判官 prompt 瘦身」未过等价性**: `ev` 2764→1096（−60%）却使 `gen` 1974→2238（+13%）
  ⇒ 本地判官 −29.6%、含本地 KPI **33.38% → 35.48%**, **但判决改变**（D1/D3/D4 FAIL; 事后按消息对齐一致率 50%）
  ⇒ 开关 `AGENTFRAMEWORK_JUDGE_PROMPT_COMPACT` **保持默认关**, **零产品变更**。机制: 判官本地成本由**生成**主导。
- **源码/工具**: `CorrectionDetector` 拆「单构造点 + Verbose/Compact 双形态」（默认关, verbose 逐字未改）;
  `channel_marks.py` **两副本**改多形态派生（识别标记 = 各形态首行公共前缀, A2 逐形态校验）
  + 零回归证据（settle 复跑 R444 归档 `32968/13 调用` 逐位同、S1 5 档案 match）。
- **候选③ 器具面并轨**: R445 三控并入 `eval/capability/instruments.json`（+2 条, 每条成对正控/负控;
  判官确定性分析器加 `--selftest` 三态 fixture）; 修 R445 **逃逸**的登记行（缺 `cmd_expect_absent`）1 行。
- **基线（同网格 M20 / 同目录消路径混淆 / 同二进制 `45b7ff73…`）**: A `61256` / BRJ `32968 + 7841`（KPI **33.38%**）
  / BRJC `33231 + 6291`（35.48%, **未采纳**）; A 臂与 R444 **逐位同** ⇒ off-path 零回归。
- **测试/AOT**: 单测 **1288/1288**（新增 K14）; AOT **0 IL**。器具缺陷登记 4 项（分析器硬编码名、settle 路径、
  端口越界、内存闸）全部已修并落 `eval/rover/r446/README-evidence.md` §D。

## v0.64.0 · R444 · 2026-09-15 · 状态: 已完成 · 主题: 廉价必要条件前置（`¬Ack ⇒ Pass`，**可证等价**）⇒ 含本地真值口径**首次转正 33.32%**

- **问题/动机**: R443 真值口径下 M20 含本地 r1 降幅 **25.32% < 30%**。缺口不在跳轮收益（远端 46.18% 已达标），而在**门的固定成本**：门在**每一轮**都问一次本地 r1（M20 = 17 次 × ≈473 tok ≈ 8037 tok），而这 17 次里只有 7 次可能被采纳为 Skip。
- **构造性论证（承重，不靠测量）**: 现网后置否决 `Skip ∧ ¬MechanicalAck ⇒ Pass` 蕴含 **`Skip ⇒ Ack`**；其逆否 **`¬Ack ⇒ 最终判决 = Pass`，与 r1 输出无关** ⇒ 把 `Ack` 判断**前移**到调用之前，对 `¬Ack` 轮直接 Pass、不建 prompt、不问 r1 ⇒ **判决路径逐位等价**，只省掉那次调用。默认开；`AGENTFRAMEWORK_GATE_PREFILTER=0` 复原 R443 行为。
- **R423 可分性预检（进实现的门槛）**: 8 个归档 BRJ 运行 × 42 门行用**驱动日志（外部真值）**对齐 ⇒ **反例 0/8**（`Skip ⇒ Ack` 全部成立）；三通道（驱动日志 / `msg_sha16` 锚点 / 块连续计数）7/8 一致；负控 `--neg-control` 必检出 ≥1 反例、`--grid-dir /nonexistent` 必 fail-closed。
- **真机读数（同网格同 NS，三臂串行）**: A **61256** / BRJ(前置门开) **32968** / BRJL(复原) **32972**；门 r1 调用 **7 vs 17**（−59%）；本地真值 **7880 vs 12775**（省 **4895 tok / 10 次 = 489.5 tok/次**）；判官侧两臂同 4738（不受影响）。
- **★ KPI**: M20 口径三档 = 远端 **46.18%** → +本地折算 39.24% → **+本地真值 33.32%（≥30% 达标；R443 同口径 25.32%）**。
- **★ 等价性（承重判据 D4）**: BRJ vs BRJL **逐轮差异 0 条**（20/20 轮 `actual` ∧ `G_calls/J_calls` ∧ 回复原文/长度全同）；两臂远端 tok 差 +4 = 已知「工作区路径入 system prompt」+1.04 tok/调用混淆（BRJL 目录名多 1 字符）。
- **质量**: BRJ/BRJL `fn=0 ∧ fp=0 ∧ acc=1.0`；A 臂 `fp=7`（不能跳）⇒ 前置门未引入任何错跳。
- **短档真值补列（D8）**: V2b **13.03%**、W8 **1.11%**（含本地真值口径）；W20 本轮**预注册排除**（k/N=1/20，增量低 + 同网格 A 分母需 20 min）⇒ 记「未测到」，不作代理。**结论：≥30% 仍只在可跳比足够大的档位成立**，但「计入本地真值后仍达标」由本轮首次做到。
- **★ 负向发现（粘滞字段，已修并验证）**: R443 的真值遥测按「上次调用值」发射，机械判定轮（未建 prompt/未问 r1）**继承**上次 r1 的真值 ⇒ M20 BRJ **6 行虚增 2382 tok**，会把 33.32% 压成 29.43%。修 = 发射点按 `gateLocalCall`（`LastBasis` 前缀非 `mechanical`）写 -1/实测值；修复版 `c28e86d3` 单变量复跑（`-s5`）⇒ 粘滞行 **6 → 0**、与 `-s4` 逐轮 **0 差异**。
- **同轮机械件（① 候选，零测量）**: L2 器具验收面 `eval/capability/instruments.json` + `instruments_check.py`（9 条器具，每条正控+负控+口径四元组）；L3 单一审计面 `eval/capability/status_gen.py` → `docs/reports/status.json`（registry/kpi/计划状态/验收矩阵全派生）；L4 写者仲裁 `tools/hooks/pre-commit`（新鲜心跳 + 异写者 ⇒ 拒）+ `tools/round_claim.sh` + `tools/install_hooks.sh`（`core.hooksPath=tools/hooks`，推送暂停令随之并行生效）。
- **诚实边界**: ① 本地 r1 只计 token 真值，未含时延/显存；② 判官侧本地成本未优化（两臂同 4738）；③ `MechanicalAck` 未放宽（不引入新跳过）；④ 短档 V2b/W8 含本地后不达标（结构性，非前置门失效）；⑤ W20 未测；⑥ 远端 tok 含 ±4 tok 路径混淆。
- **下轮候选**: ① 判官侧同类前置（找 J 的机械不变量）；② W20 补列 + 真实 API 口径复核；③ 前置门在**多跳簇/早期跳**网格的行为（t2–t6 型「terse_new」是否可再压）；④ L2/L3 接线进 CI（`instruments_check` 作提交前闸）。
- **计划/证据/登记**: `docs/plans/v0.64.0-r444-cheap-necessary-condition-prefilter.md`；`eval/rover/r444/README-evidence.md`；`docs/verification-registry.json` → `r444.*`（7 行）；`eval/capability/kpi.jsonl` → R444。

## v0.63.0 · R443 · 2026-09-15 · 状态: 已完成 · 主题: 本地 r1 成本 **tokenizer 真值化** + 「被跳轮不回放」**同网格单变量消融**

- **问题**: ① 本地 r1 的真实 tokenizer 成本 vs「字符/2」折算的偏差方向与幅度？②「被跳轮不回放内联块」的真机单变量效应 vs R442 的离线代数分解？
- **产品侧改动（默认零行为回归）**: `RecordCachePinned` 增记 llama-server 上报的 `tokens_evaluated/prompt_n/gen`（`LocalGenerationPort.cs`）；`RelationJudgeOutcome` 增 `PromptTokens/PromptNewTokens`；`local_turn_gate`/`correction_judge` 遥测增真值字段；新增诊断开关 `AGENTFRAMEWORK_GATE_REPLAY_SKIPPED`（默认关）。AOT `127b4ff5…`，0 IL 警告，V0 形态闸 PASS。
- **读数（M20 同网格三臂）**: A 61256 / BRJ 32968 / BRJRP 39508；
  `D_remote` **46.18%** → +本地(R442 字符/2 折算) 33.25%（逐位复现 R442 的 33.26）→ **+本地(真值) 25.32%**。
- **★ 真值化结果**: 本地合计折算 **7919.5 → 12775 = 1.613×**（门 prompt 1.398×、门生成 1.267×、判官 prompt 1.496×）；轮均本地成本 c=**638.8 tok**（折算口径 396）；转正闭式 `k/N > c/s` = 15.81%。
  ⇒ **「≥30%」只在「用户 API token」口径成立；含本地 r1 真值口径下 M20 = 25.32% < 30%**（口径必须绑定，不得混算）。
- **★ 单变量消融**: Δ 实测 **6540 tok** vs R442 离线代数分解 4830.5 ⇒ **离线分解低估 26%（1.354×）**；R442「实测偏保守」的方向成立、幅度被修正。
- **记账**: `tokens_evaluated == prompt_new + cache_n` 门 17/17、判官 13/13、**违规 0**；开关可机检（`replay_skipped` 0→1、`dropped_sum` 2024→0）；ρ(micro_step) token **恒 0**（对 token 判据零影响，触发条件仍 undetermined）。
- **D4 预注册被证伪 + 收窄**: 跨 NS 逐位比较 Δ=+18（11 轮 +1~2）⇒ 判红；由两独立通道定位为**路径后缀混淆**（D2b: A 臂对 61230→61256 = **+1.04 tok/调用**，同二进制仅目录名不同；D4b: 无 NS 同名臂 vs R441 归档 **逐轮 0 差异 / 32950==32950**）⇒ 零回归成立（事后判据单列，不改写预注册）。
- **诚实边界**: ① 真值只覆盖 M20 一列（短档/单跳档仍折算口径）；② 真值=该构建分词器，**不等于计费口径**（未测真实计费/时延）；③ `BRJRP` 是诊断臂非产品路径；④ D5 的 ±20% 预注册未命中，结论以「离线分解低估 26%」表述。
- **下轮候选**: ① 零测量落地**验收矩阵 + status.json 生成器 + 器具闸**（见 `docs/reports/endpoint-and-audit-contract.md`）；② 真值口径补测短档(V2b)/单跳档(W8/W20)；③ **压低 c**：门前置筛选（只在可能 skip 的轮跑门）⇒ 低占比档转正；④ 写者心跳 + pre-commit 仲裁（R443 双写者实发）。
- **计划/证据/登记**: `docs/plans/v0.63.0-r443-local-token-truth-and-replay-ablation.md`；`eval/rover/r443/README-evidence.md`；`docs/verification-registry.json` → `r443.local-token-truth-and-replay-ablation`；`eval/capability/kpi.jsonl` → R443；架构提案 `docs/reports/endpoint-and-audit-contract.md`。

## v0.62.0 · R442 · 2026-09-15 · 状态: 已完成 · 主题: **口径钉死**（本地 r1 入账）+ 两臂块不对称定量 + D7 分母断言

- **背景**: R441（`40748e0`，4 网格 8 臂同网格实测）留下三条挂账 —— 降幅口径只算远端 G、A/B 两臂内联块不同源但幅度未定量、A 分母跨网格代理已复发两次。
- **做法（纯离线, 零源码改动/零 dotnet/零新真机跑）**: 对 R441 已落盘档案复算。器具 `eval/rover/r442/{token_accounting.py,design_check_r442.py}`；预注册 = `docs/plans/v0.62.0-r442-accounting-and-asymmetry.md` §2。
- **读数 1 · 口径三档（同档案只换加项）**: ①远端-only W8 13.77 / W20 3.20 / M20 46.19（**逐位复现 R441**）②去块内容不对称 13.77 / 4.94 / 45.01 ③**含本地 r1**（门提示+门生成+本地判官，字符/2）**−2.06 / −10.92 / 33.26** ④最严 ②+③ −2.06 / −9.17 / **32.09**。
  ⇒ **「≥30%」只在远端 API token 口径下普适**；含本地成本后仅 7/20 中簇达标，单跳格（1/8、1/20）**转净亏**。KPI 必须携带口径标签，缺标签的 ≥30% 属空心宣称。
- **读数 2 · 转正闭式（3/3 命中）**: 含本地口径转正 ⟺ `k/N > c_local_per_turn / s_per_skip`（c ≈ 341/383/396 tok·轮⁻¹ —— 门在**每个非机械轮**都跑 ⇒ 本地成本 ≈ 常数×N；s ≈ 2376/1736/4040 tok·跳⁻¹）。观测 12.5%<14.37% 亏、5%<22.09% 亏、35%>9.79% 盈。
- **读数 3 · 不对称定量（更正 R441）**: Σasym = 0 / **+949.5** / **−5551.5**（M20 拆 −4830.5「被跳轮不再回放内联块」= 机制真实效应 + −721「块内容差」）。⇒ R441「两臂块不同源 ⇒ 实测偏保守」**方向断言被证伪**：M20 反号，去掉块内容差后 46.19% → **45.01%**（原测偏乐观 1.18pt）。
- **读数 4 · D7 断言上线**: A 分母必须同网格同值 + 主调用轮 ⊆ [1,N]；6 网格全绿，**两例负控判红**（NC1 = 注入 R440 真实缺陷「W8 用 V4 全长 61281」，NC2 = 网格标签不符），正控 PASS ⇒ `D7_pass=true`，复发路径被封。
- **读数 5 · ρ 清点**: 跳轮本地消费回复 190 / 353 / 127–515 字符（9 事件/3 网格）；条件不可控 ⇒ 判 **`undetermined`**，下一轮实验设计已登记。
- **基线**: 入口 `40748e0`(R441) ⇒ 本轮 commit（离线器具 + 台账，无产品代码变更，AOT 无需重发布）。
- **诚实边界**: 离线复算无 AOT/真机新跑（L2）；本地折算 = 字符/2 **非 tokenizer 真值**（M20 真值 ±20% ⇒ 31–35% 带内仍达标，单跳格负号不翻正）；③ 口径的**归属**未替用户裁定；② 非完整单变量（真单变量需同网格开关「[已完成] 累积」）。

## v0.60.0 · R440 · 2026-09-15 · 状态: 已完成 · 主题: 一轮任务降幅的**分档实测**（长度梯 + 位置单变量 + 无设备负控）

**完成记录**（零产品源码改动, 被测 = /tmp/pub_r438/agenthost AOT native）:
- 分档实测（远端 token 口径, 同网格 A 臂分母）: 单次 N=1 **−3.95%**（净亏）｜短 N=4 可跳 1/4 **+32.24%**｜中 N=8 **37.90%** / N=12 **37.37%**｜长 N=20 散布 **45.31%** / 晚簇 **48.57%**｜长 N=20 零可跳 **−2.40%**｜负控（无设备·晚簇）**−5.47%**。
- 质量: 全 BRJ 臂 `fn=0 ∧ fp=0 ∧ acc=1.0`（V5 含 7 条未经 r1 实测的新文本 ⇒ 强检验通过）; A/BRJ 的澄清吞并集合逐网格一致。
- 位置单变量: V4（晚簇）− V20（散布）= **+3.26 pt**（晚簇更省）; 预注册模型给 ≈ −1.2 pt ⇒ **C7 FAIL**。
- 预注册判据: **C1/C4/C5/C6 PASS**；**C2/C3/C7 FAIL**，逐条根因**在预测器**: ① A 分母跨网格逐记录下标代理（+9.25%）② 被跳轮在 A 臂的成本被漏计 ③ δ(i) 线性外推。
- 事后校核（checks_posthoc, 单列）: **δ ≡ 77 tok 常数**（5/5 网格逐轮一致）+ 同网格 A 臂分母 ⇒ 重锚模型 **5/5 ≤ 0.47 pt**; 二阶项 = 被跳轮「从未发出内联块」不再回放（散布 2227 tok, 晚簇 ≈0）。
- 器具自捕: `design_check.py` 追回**本轮自身**的 expected 轮号偏移; `predict_r440.py` v1（逐文本匹配 A）自查废弃并留档。

**基线**: HEAD `a0d1ba2` → 本轮提交（未 push, `.git/PUSH_PAUSED` 在位）。器具: `eval/rover/r440/*`。计划: `docs/plans/v0.60.0-r440-length-ladder-measurement.md`。

## EXP1-Q7 · 文档侧定点修复（改写失效路径 + 补退役标记）与「桶归零」的空心绿（60m 自检作业）

**主题**：附录 G.7 结转「把 `relocated` 的 10 条定点可改 + 3 条写法漂移 做文档侧定点修复，并对 `retired_after_write` 引用补退役标记 —— 改动只碰文档，复跑仪器断言两桶归零」。

**判决**：① 文档侧定点修复完成，**只碰 10 个文档**（行数逐文档不变）：`relocated` **13→0**、`stale_path` **21→8**、`retired` **8→21**、`ok` **741→753**、`symbol_absent` **65→66**（唯一迁移项在修前 `relocated_fact_verdict` 即为 `symbol_absent`）、`stale_lines 4`、`waived 70` 未动。② 预注册 P1–P5 **全过**；③ 仪器 v2.3.0 复跑**两跑逐位相同**、自证闸 G1–G6 全 true、`--selftest` exit 0。④ 余 8 条 `stale_path` = 弃权类 `same_commit_as_deletion`（同一删除提交的 8 处），按预注册**零动作**（补标记会把弃权类并入 `retired`，抹掉 G.2 建立的区分）。

**本轮核心发现（自捕测量层缺陷 D1，比修复本身更重要）**：首版修复器按路径**子串**定位插标记 ⇒ 标记落在「路径」与「`:行号`」**之间** ⇒ `CITE_RE` 不再匹配该 token ⇒ **13 条引用从语料中消失**。危险形态在于**目标桶全部"达标"**（`relocated` 13→0 ✓、`stale_path` 21→8 ✓、`exit 0`、两跑逐位相同 ✓）—— **桶判据在缺陷态会放行**。暴露它的是**桶账不平**：`ok +12` 与 `symbol_absent +1` 只能解释 13 条改写，**13 条被标记引用的去向无处安放** ⇒ 语料引用总条数 **922→909**。⇒ 补进预注册的 **P6 计数守恒不变量**：任何改写语料的动作必须断言「引用总条数不变」（修复器层逐文档 + 全语料）。

**修改**：新增 `eval/capability/exp1-q7/{apply_doc_fixes_q7.py(v1.0.0→v1.1.0), prereg_q7.json, edit_plan.json, edit_plan_v100_defect.json, edit_plan_d1_negative_control.json, attribution_q7_{before,after,after_rerun,after_D1repro}.json, selftest_q7_after.txt, README-evidence.md}`；计划文档 **附录 H**；本条目 + `eval/capability/kpi.jsonl`。**未动 `src/`、未动 `skills/`、未动登记表**。

**读数**（修前→修后，仪器 v2.3.0，178 文档 / 594 只读输入逐文件 sha256）：`relocated 13→0`、`stale_path 21→8`、`retired 8→21`、`ok 741→753`、`symbol_absent 65→66`、`stale_lines 4→4`、`waived 70→70`、**引用总条数 922→922**。**负控（可复现）**：`--insert-mode=path_end` 复现 D1 ⇒ 修复器层条数 `582→569`、`count_invariant_ok=false`、`verify_bad=13`（全 `MARK-MISSING`）、`exit 2`；仪器读数落缺陷态档案（**总条数 909，而桶面同样"绿"**）。**绑定仪器真实行为**的读回校验（非文本代理）：13 条改写复跑抽取 + `judge_citation` ⇒ `ok 11 / symbol_absent 1`；13 条标记 ⇒ **`retired` 13/13**。

**基线**：本轮前 HEAD 工作树（本地，未推送；`.git/PUSH_PAUSED` 在位）。证据等级 **L1 静态机检**。形式校验：对侧 30m 主线作业在跑 R440 网格（`eval/rover/r440` + `docs/plans/v0.60.0-r440-*` 为在途产物）⇒ 按「测量纯净闸」**不跑 `dotnet`**，形式校验**结转**（与前两轮同）。

**诚实边界**：① L1 静态，无编译/单测/AOT/真机运行；② 语料是**移动目标**（对侧在改 `src/`/`docs/`）⇒ 读数与 HEAD 绑定，确定性由两跑逐位相同 + 594 输入指纹归因；③ **「两桶归零」按可动作类解读**（`relocated` + `retired_after_write`，两者均 0）——若字面读作 `stale_path→0`，须先裁定那 8 条的语义，**禁止用标记把弃权类洗成 `retired`**；④ `symbol_absent 66` 是全文匹配启发式（非 AST），只作候选不作结论，本轮既未引入新缺陷**也没有修好它**；⑤ 退役标记只声明「路径在 HEAD 不存在 ∧ 删除提交为 HEAD 祖先」，不声明引用何时成形；⑥ 标记/替换串一律由产物派生（仪器常量 + 复核器 `sha7`）并**读回比对码位**，未复现 F.3 的写入通道改写；⑦ 附录 H 正文写入后**复跑仪器零新增引用**（自指控制 922=922）。



## EXP1-Q6 · 全仓失效引用的四级归属复核：时间轴锚点 +「当前不成立」vs「写成时就错」（60m 自检作业）

**主题**：附录 F.5 结转「按同一四级归属**逐条复核全仓剩余 `stale_path 21`**」。本轮把仪器 v2.3.0 判定的 `stale_path` **21** 条 + `relocated` **13** 条（10 文档）**逐条**做完归属复核，并补上仪器未建模的第四级：**时间轴**。

**判决**：① 复核器落地（新件，与仪器解耦，只消费读数 JSON）：`eval/capability/exp1-q6/attribute_failed_refs.py` **v1.2.0**，自证 **18/18** 绿（含**真版本库夹具**三样本：退役前成形 / 退役后成形 / 与退役同提交 ⇒ 必须落**三个不同类**，证明判据两向可分、非恒真非恒假）。② 读数：`stale_path 21` = **retired_after_write 13** + **same_commit_as_deletion 8**，**`dead_after_delete` 0**、`axis_disagreement 0`、`no_deletion_commit 0`；`relocated 13` = **fixable_direct 10** + **path_elision 3**（写法漂移：路径里含省略号）；复核器 **exit 0**。③ 删除侧外部真值齐备：10 个文件**全部**有删除提交且均为 HEAD 祖先（`b00917c` 本地 GGUF 引擎整线退役 9 件 / `af9856b` 插件注册表退役 1 件），全树**无过滤**同名搜索 0 命中（独立于仪器过滤面复核）。

**关键结论（语义澄清）**：**「当前不成立」与「写成时就错」是两个判据**。上一轮只做到前者；本轮补后者后，语料中**「写作时即失效」的引用 = 0** ⇒ 那 21 条引用的**当前无效性**仍由 L-1/L-2/L-3 外部真值证成，属**文档时效维护**对象（补退役标记 / 改写路径），**定级不是缺陷指控**——混为一谈会在批量退役提交上产生成片假红（本轮实测：v1.0.0 锚点取「文档最后修改提交」⇒ 7 条假红；v1.1.0 串级检索未跟随重命名 ⇒ 1 条假红）。

**修改**：新增 `eval/capability/exp1-q6/{attribute_failed_refs.py, result_q6_before.json, result_q6_after_docs.json, attribution_q6_v120.json, selftest_q6_v120.json, make_evidence.py, README-evidence.md}`；计划文档 **附录 G**；本条目 + `eval/capability/kpi.jsonl`。**未动 `src/`、未动 `skills/`、未动登记表**。

**读数**（仪器复跑对照，证明新证据不引入新引用）：`stale_path 21→21`、`relocated 13→13`、`symbol_absent 65→65`、`stale_lines 4→4`（判据 G1–G6 全过，exit 0）⇒ 附录 G 正文**零 `src/` 路径字面量**，自指假红为 0。

**基线**：本轮前 HEAD `7be1d54`（本地，未推送；`.git/PUSH_PAUSED` 在位）。证据等级 **L1 静态机检**。

**诚实边界**：① L1 静态，无编译/测试/真机运行；② 8 条「与退役同提交」是**弃权不是清白**（一次提交既退役文件又写入文档 ⇒ 时间轴同形不可分，要判别需变更前快照，时间戳无用）；③ 时间轴只锚**版本库历史**，未入库文档无锚 ⇒ 弃权（本档 0 条）；④ 语料是**移动目标**（对侧作业在改 `src/`），读数与 HEAD 绑定；⑤ 本轮**三次测量层自捕**（锚点取错层 / 未跟随重命名 / 同提交误落歧义分支），均**先修仪器再谈被测**；⑥ `relocated` 的 10 条定点可改 + 3 条写法漂移**本轮未修**（只复核，不改文档）⇒ 结转下轮。

## EXP1-Q5 · 续引 `[:NNN]` 形态建模（仪器 v2.3.0）+ exp1 §1.4/§1.5/§3.3/§4.2 引用定点修复（60m 自检作业）

**主题**：exp1 档剩余失效引用（附录 D 结转 3 真删 + 9 搬家）＋ 附录 E 结转的「续引 `[:NNN]` 形态建模」。执行顺序：**先补测量盲区，再修文档** —— v2.2.0 既不认出续引形态也无归属规则 ⇒ 本档 **51 条续引从未被检查**（保守漏检）。

**判决**：① 仪器 **v2.3.0** 落地：续引归属四级（T1 反引号内 `Stem.Member` 主干唯一映射 / T2 同行最近前引 / T3 块内前序路径集合唯一 / T4 弃权单列）+ **留痕继承**（同行 ∧ 同路径的带标记引用覆盖该续引）+ 新判据 G6（子探针非退化），自证 **14 → 37/37**；② 本档 `stale_path` **3→0**、`relocated` **9→0**、续引非绿 **5→0**（续引 `ok` 40→44）；③ 全仓 `stale_path` **24→21**、`relocated` **22→13**、`retired` **5→8**、`ok` **724→734**；判据 G1–G6 全过（exit 0）。

**修改**：`eval/capability/exp1-q4/probe_doc_ref_integrity.py`（v2.3.0）；本档 **11 行**修复（3 处真删加退役留痕 / 9 处写法漂移改真实路径 / 1 处续引改显式路径 / 2 处行号事实漂移 `docs/api.md 1409→1410` / 1 处符号名漂移 `SessionMemoryStore→JsonSessionMemoryStore`），`git diff` **11+/11−**，无标题/锚点变更、行号未位移；新增证据 `selftest_v230.json` / `result_v230_{before_fix,after_fix,final}.json` / `ab_diff_v230.md` / `continuations.jsonl` / `gate_check_exp1q5.json` / `form_check_evidence_v230.txt` / `probe_stdout_v230_*.txt`；计划文档 **附录 F** + `eval/capability/kpi.jsonl`。

**读数**（176 文档 / 591 只读输入逐文件 sha256；修前→修后）：本档完整引用非绿 **12→0**（余 2 条 `symbol_absent` 均为附录 E.3 已裁定的**主语型启发式假阳性**，未改文档）；续引 `retired` 6（其中 5 条由**留痕继承**判入：L52 注册表续引 + L67 四条 —— 其锚点引用已登记退役）。

**基线**：本轮前 HEAD `83f04e7`；本轮提交 = `0af65fc`（本地，未推送；`.git/PUSH_PAUSED` 在位）。**形式校验（附录 D/E 三度结转）本轮清账**：`dotnet test --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒ **Failed 0 / Passed 13 / Skipped 0 / Total 13 / 338 ms（exit 0）**；**闸门判定理由外显**：`MemAvailable 2668 MB`（阈值 2800）、`pgrep` 计数 2 = Roslyn `VBCSCompiler` 常驻编译服务器 + **自匹配** ⇒ 按「测量纯净闸」原意（防与**在途**构建/测量互撞）判可跑：无在途 `dotnet build/publish/test`、无 `agenthost`、无 `llama-server`、`loadavg 0.10`、对侧工作树 clean。

**诚实边界**：① 证据等级 **L1 静态机检**（无编译/测试/AOT/真机运行）；② 续引 T1–T3 只有**有证据**时才认，不成立一律**弃权单列**（不判红）⇒ 未认领续引不判红；③ 续引**不查符号**（符号归其锚点引用）⇒ 与符号启发式读数分开计；④ T2/T3 是**位置**证据 ⇒ 语义所指与最近前引不一致时会**错锚**（本档 L68 实测一次：续引被错锚到 137 行的 `LlamaCppTextEmbedder.cs`，实际所指为同文件 `ServiceCollectionExtensions.cs:225-242` 的 RAGConfig DI 工厂）⇒ 处置 = **把路径写显式**，不改判据；⑤ 全仓仍有 `stale_path 21 / relocated 13`（集中他档，本档清零）；⑥ 语料是**移动目标**（对侧 30m 作业在改 `src/`），确定性由两跑逐位相同 + 591 输入指纹归因；⑦ 本轮两次踩到**写入通道改写手打字面量**（长字面量里的斜杠被改成点、路径字面量匹配 0 命中）⇒ 替换串一律由**行内 token / 正则**派生、标记常量由**码点**构造；⑧ 「**记录缺陷的文本本身会被机检当活引用**」实测一次（附录 F 初稿把修复前原文写进正文 ⇒ 本档续引 waived +1 / stale_lines +1）⇒ 引用示例必须入**代码围栏**；⑨ 未动 `src/`、未动登记表（`docs/verification-registry.json`）、未新增/改 `skills/`。

## EXP1-Q4 · 引用探针符号归属修复 + exp1 §1.2/§1.3/§4.4 引用定点修复（60m 自检作业）

**主题**：exp1 §1.2/§1.3/§4.4 失效引用（附录 D 结转）。执行顺序：**先修测量，再修文档**——附录 D 的 `symbol_absent` 读数经复核含测量层缺陷，照它改会误杀正确引用。

**判决**：① 仪器缺陷成立（判据被证伪）：符号按**整行**共享 ⇒ 一行多引用时互相污染、虚高。同输入 A/B 证明 **74 条** `symbol_absent → ok`、**零** `ok → 非 ok`（无回归；污染是单向虚高 ⇒ 修复不暴露被掩盖的真缺陷，如实登记）。② 本档 §1.2/§1.3/§4.4 定点修复完成：`stale_path` **5→0**（5 条全部改注退役留痕）、`relocated` **5→0**（改真实路径）、`symbol_absent` 3→2（余 2 条经 grep 复核裁定为**主语型启发式误报**，未改文档）；整档 `stale_path` 8→3、`relocated` 14→9、`symbol_absent` 18→2。

**修改**：仪器 **v2.2.0**（`eval/capability/exp1-q4/probe_doc_ref_integrity.py`）——符号**逐引用就近归属**（整行配对一次，防窗口切片错位）+ 新增 `retired` 判定（显式 `【已删 <commit>】`/`【已退役 <commit>/<R>】` 标记，60 字符窗且不越相邻引用）+ `--selftest` **14/14**（正控/负控各 5 类）；本档 9 行修复（8+/8−，无标题/锚点变更）；计划文档 附录 E + 本条目 + backlog 状态行 + `eval/capability/kpi.jsonl`。

**读数**（174 文档 / 同输入 A/B，语料 905→906 条）：`ok` 651 → 709 → **716**；`symbol_absent` 124 → 66 → 65；`stale_path` 29 → 29 → **24**；`relocated` 27 → 27 → **22**；`retired` 0 → 0 → **5**；`relocated_fact ok` 12 → **25**。

**基线**：本轮前 HEAD `d84ccf2`（本地提交，未推送；本轮提交主题 = `EXP1-Q4: 引用探针符号归属修复 + 本档 §1.2/§1.3/§4.4 引用定点修复`）。**形式校验本轮未跑**：对侧 `agenthost` + 2×`llama-server` 在跑、`MemAvailable 1702 MB < 2800 MB` 闸 ⇒ 按「批测与 build 互斥」避让并**结转**（命令见 exp1 附录 D）。

**诚实边界**：① 证据等级 **L1 静态机检**；② `retired` 是**约定标记**（判据绑"标记出现"，负控 = 无标记或标记越窗仍判 `stale_path`）；③ 归属修复偏差方向为**保守漏检**（符号未被任何引用窗口认领时不做检查）⇒ 下轮候选 = 续引 `[:NNN]` 形态建模；④ 本档仍有 3 条真删 + 9 条搬家（§1.4/§1.5/§3.3/§4.2）；⑤ 本轮未动 `src/`、未动登记表与技能。

## EXP1-Q2 · 计划前提核验：被引契约已删 + 文档引用事实机检（60m 自检作业）

**主题**：exp1 §8-Q2（插件 API 是否引入 manifest + `schema_version`）——先把「复用既有契约（不新造）」这个**前提**核验掉，再谈选项。

**判决**：**前提为假**（机器判）。`ICapabilityPlugin` / `PluginExecutionResult` / `CapabilityPluginRegistry` 在当前 `src/**/*.cs` 出现 **0 次**（正控 `IResponseSegmentPlugin` 24 / `CapabilityScanner` 12 / `PythonArtifactPlugin` 19 证明计数器非恒 0）；`src/agent/registry/CapabilityPlugin.cs`（118 行）与 `src/agent.tests/CapabilityPluginTests.cs`（75 行）在 **af9856b**（2026-09-13, v0.23.0 R386/R387）被删除，且该提交是 HEAD 祖先。

**根因**：exp1 §1.2/§1.3 是按 `docs/reports/r385/capability-inventory.md` 抄写的 r385 盘点，**早于** R386/R387（契约删除）与 **b00917c**（2026-09-14, R408「本地 GGUF 引擎整线退役」，70 文件 / −11,039 行，`BgeCpuEmbedder`+`src/agent.embedcpu/` 整条线）⇒ 整节承载实现已不存在或被重排（本仓并存 `src/agent.<模块>/` 与 `src/agent/<模块>/` 两种写法）。

**修改**（零产品源码改动、零 dotnet）：新增 `eval/capability/exp1-q2/{probe_doc_ref_integrity.py(v2.1.0), selftest_doc_ref_integrity.py(21 项自证)}` + `result.json`/`citations.jsonl`/`selftest_result.json`/`git_deletion_evidence.txt`/`probe_stdout.txt`/`append_kpi.py`；计划文档补 附录 D + §1.2/§1.3 校正块 + §4.4 前提证伪块 + §8-Q2 行。

**读数**（174 文档 / 896 条 live 代码引用 / 589 只读输入逐文件 sha256 指纹）：`ok` 649 · `symbol_absent` 119（启发式候选）· `waived` 68（弃权）· `stale_lines` 4 · **`stale_path` 29（真删）** · **`relocated` 27（搬家）**；本档自身 = 真删 8 + 搬家 21。裁定数据：capability-id 分派契约 **0** / 带版本字段契约 **0** / manifest 先例 **0**（DI 静态注册 53）⇒ D1 `no_existing_carrier`（契约须新建，新建即带 `schema_version` 零迁移成本）、D2 `needs_new_loader`（**不推荐** manifest 形态）。

**仪器缺陷（本轮自捕两处 + 自检一处）**：① v1 把无目录裸文件名判 `stale_path`（首读 **389 条虚高**）⇒ 三级归属 + 弃权单列；② v2 未区分**已删除**与**树内搬家** ⇒ 第四级 `relocated`（0 候选才判真删）；③ 自检抓出「不存在的仓库被判红（应弃权）」⇒ 前置结构检查 + 测量有效性闸。修后仪器自证 **21/21 绿**。

**基线**：HEAD `053edbb`。**形式校验（附录 C 三度结转）本轮补跑清账**：取得对侧空闲窗口后执行 `dotnet test --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒ **Failed 0 / Passed 13 / Total 13（914 ms, exit 0）**，证据 `eval/capability/exp1-q2/form_check_evidence.txt`（起跑条件：对侧近 3 min 无产品源码写入、`MemAvailable ≈ 2.6 GB`）。前两次因对侧在途构建/正在编辑产品源码按「批测与 build 互斥」避让，记录在案。

**诚实边界**：① 证据等级 **L1 静态机检**（无编译/测试/AOT）；② `symbol_absent` 是全文匹配启发式，不作结论；③ 只判「引用事实是否成立」，不评价计划内容对错；④ 本机读数是对移动目标（对侧在改 `src/`）的快照，确定性由两跑 + 输入指纹归因证明；⑤ 与附录 C 旧登记「引用路径 6/6 存在」冲突：旧口径过窄，**作废不再引用**（口径变更已登记）。

---

## R433 · 文档跑测链复位 + 取码产物通道（同题假红裁决）

**主题**：用户纠偏令——「仔细审查有没有偏离主题…没怎么严格执行文档中的跑测计划，不看数据只开发是不行的」⇒ 回到 `eval/probe/README.md` 跑测链执行并看数据。

**偏离审查（机检）**：KPI sink `data/probe/kpi.jsonl` 停摆 ~21h（末行 09-13T23:20, 6 行），run 摘要 30 份中 24 份未打点；exp14 M6「扩族+常态化」仍 ⏳；近 8 轮（R424–R432）读数只进 `eval/capability/kpi.jsonl`、**0 行进 KPI sink**。

**判决**：**PASS（链复位）** ∧ 裁决「同题质量无退化」。冻结题集 sha `b8e796a6d803918d`：基线 09-13 `1.0000`(36/36, 215.01s) → 旧仪器 run1/run2 **`0.6944`**（各 1 题 `syntax_error`, 题不同）→ 修后 fix/fix2 **`1.0000`**(36/36)；抗饱和族 3/3（43/43）；判别力负控三族整题 **0/3**（topo_dfs 0.4359 / vm_noerr 0.6250 / json_loose 0.7037 用例级）。

**根因**：判分取码取自**渲染后的对话转录**（TUI 吃掉围栏与 `__x__`, 候选只剩装饰片段 ⇒ `SyntaxError: invalid character '｜' (U+FF5C)`），而产品遥测 `script_artifact` 已记 `origin=fenced` + `compile_valid=true`（3/3 程序题）⇒ **旧读数 100% 假红**。

**修改**（本侧仅评估面, 零产品源码）：`eval/probe/grade.py` 取码新增落盘产物外部真值通道 + `code_source` 可见；`eval/probe/run_probe.py` 遥测收割产物（闭区间进程窗口 ±0.25s, 时间戳 7 位小数容错且不可解析 fail-closed）。自检 `grade` **34/34**、`run_probe` **29/29**（新增 6 条含正/负控）。

**台账复位**：`scripts/kpi_probe.py` 追加 `data/probe/kpi.jsonl` **6 → 14 行**（+8）；A/B 段「同批题集 ⇒ Δ 可比」质量 Δ `+0.0000`；成本 `tokens/题` 6021.8(旧 run1) / 6001.3(fix) / 6032.7(fix2)，墙钟均 15108/20362/31652 ms。

**基线**：`/tmp/pub_r433/agenthost`（HEAD 发布, IL 告警 0, sha256 `a2b3f421…`, 15,184,624 B）。

**诚实边界**：① 不宣称 token 变化（基线在遥测窗口外 ⇒ `tok/题 = n/a`; fix 臂间 6.0k–9.2k 落在远端模型噪声带）；② run2 假红只证「同机制、同 mode、同病因」；③ 墙钟方差 91.97→191.57s ⇒ 不作能力判据；④ 离线复放归属不精确 ⇒ 只作机制验证、不采信为读数；⑤ 抗饱和族题集 sha 与 R417 不同 ⇒ 该行非同题 A/B；⑥ 单机单次。

## R432 · 门判判别力与确定性成对（残余带内）

**主题**：补 R429 诚实边界 ④（判别力负控落空）——钉死判定路径后，门**还能不能区分**「新诉求 / 无新诉求」，且同文重复逐位恒定。

**判决**：臂 2 = **FAIL**（规则：PASS = C1 and C2ack and C2cont and C3 and C4 and C5; PARTIAL = (not C1) and C1p and C2ack and C2cont and C3 and C4 and C5; FAIL = (not C3) or (not C4) or (not C5); UNDECIDED = no r1 reading）；臂 1 = n/a（族位错配，非仪器失效）。

**臂 2 机检读数**：门记录 12（r1 11 / 机械 1）；r1 判决 ["Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip", "Skip"]；raw_len ["474", "474", "323", "323", "185", "185", "185", "185", "261", "261", "170"]；进门位 [1, 2, 4, 6, 8, 10, 11, 12, 13, 14, 16, 18]；归因 alignment=True attribution=False；远端调用 9 / token_est 2434

**基线**：R430 同文 4 次门判 raw 同一（127/127/127/127）且判决 Skip×4（确定性已证）。

**仪器**：新增门判定**时间窗对齐**（telemetry ts 落入轮时间窗，废弃 secs>=5 位置启发式）；实测可达位偏移 = 奇数位（seed 轮问询被下一轮 ask 消费）。

**撞号登记**：R431 被对侧并发作业先占（未提交工作树）⇒ 本侧让号至 R432 / v0.53.0。

**证据**：`eval/rover/r432/README-evidence.md`

---

## R430 · 判定输入指纹 ⇒ 服务端总槽位：决策路径**逐位可复现**（R429 遗留 P5c 收口）

**主题**：把 R429 的「弱宣称（判定**输入**不可复现）」升级为**强结论（同一输入 ⇒ 逐字节同一输出）**。

**因果链**（证据：`eval/rover/r430/README-evidence.md`，由机检 JSON/日志生成）
1. 只观测地加**输入指纹**三层：prompt（送达服务端的渲染后文本）/ 请求体（全字段 JSON）/ 角色种子。
2. 真机（臂 C / k8r，改动前二进制）：4 次门判 `prompt_sha`、`request_sha` **各只有 1 种取值**，
   而输出 raw 逐字节哈希 **4 种**（122/129/113/111）⇒ 输入恒定、漂移在**引擎侧**（H1 证伪）。
3. 机制（传输级探针 `concurrent_probe_v2.py`）：本仓库 llama.cpp 构建 `-np` **默认 = 4 槽**
   （启动日志 `n_slots = 4` 实证）⇒ 门判与关系判官等**并发在途**请求进同一批 ⇒ 每序列批形状/分块
   随调用序列变化 ⇒ 浮点归约顺序变 ⇒ 同一输入走出不同轨迹（105/105/108 tok；串行基线 75）。
4. 修法：本地通道服务端**显式** `-np 1`（真串行；绝不依赖构建默认）⇒ 并发探针 3/3 逐位相同；
   真机同文 4 次门判 raw 逐字节**同一**（sha16 `340ba10faeb3a0a8` ×4），判定仍 `Skip×4`，cache_n 恒 0。

**产出**

| 产出 | 路径 | 机检读数 |
|---|---|---|
| 输入指纹（四层贯通，只观测） | `src/agent.modelqueue/LocalInputFingerprint.cs` + `LlamaCppClient`/`LlamaCppTextGenerator`/`LlamaCppLocalGenerationPort`/`ModelQueueRouter`/`IndustrialAgentV2` | 门判遥测新增 `prompt_sha`/`request_sha`/`req_fields`/`role_seed_sha`；默认路径零回归 |
| 显式总槽位 | `LlamaServerHost.BuildArgumentList`（纯函数）+ `LlamaServerOptions.Parallel=1` + `ModelCatalog local.parallel` + DI 接线 | `-np` **无条件**出现，默认 1；`Parallel≤0` 夹到 1 |
| 新测 | `src/agent.tests/{DecisionPromptFingerprintTests,LocalServerParallelTests}.cs` | 门禁子集 **26/26**；全量 **1242/1242** |
| 机制探针 | `eval/rover/r430/{concurrent_probe_v2.py,probe-r430-concurrent-v2.json,server-probe.log}` | P1 串行同一；P2 并发变体 2；P4 强制 `-np 1` 变体 1 |
| 真机两臂 | `eval/rover/r430/{verdict-C-k8r-r430post1.json,verdict-C-k8r-r430fix1.json}` | pre 4 种 raw / fix 4/4 同一；KPI 远端 2→1、token 2053→1996 |
| 形态 | `/tmp/pub_r430b/agenthost` | IL 警告 **0**；15,180,528 B；sha `bb104dd7…`；V0 闸 AOT 原生 + IL 负控拒 |

**判据（预注册，见 `docs/plans/v0.51.0-r430-input-fingerprint.md`）**：P1 串行同一 ∧ P2 并发可复现漂移
∧ P3 输入指纹恒定 ∧ P4 强制 `-np 1` 后同一 ∧ P5 判定与 KPI 不退化 ⇒ **PASS**（P3 前置在前，落在 H2 分支）。

**诚实边界**：① 未测修法后判定/回复**质量**变化（只测可复现性与 KPI 计数）；② `-np 1` 的代价是本地通道真串行，
墙钟增量未量化上限；③ G3（`-np 2` + `id_slot`）本次亦稳定，但依赖每次调用钉槽位 ⇒ 只作备选记录；
④ 探针 v1 有「渲染早于起服务」与末段取值 bug（v2 已修并增量落盘）；⑤ 单机单次读数。

**下轮候选**：① 门判与判官在 `-np 1` 下的墙钟/排队曲线（量化串行化代价）；② 打点把规则层单列 `rule`；
③ 构造能进 r1 门的新诉求网格（补 R429 判别力负控缺口）；④ `docs/improvements.md` 更早区段（R416/R412/R403 等）仍在乱序位，待重排。

## R429 · 决策路径缓存态钉死（门判 / 关系判官）

**问题（因果链）**：门判与关系判官共用同一个本地推理进程的**单 slot 前缀缓存**（`LlamaCppLocalGenerationPort` 一律 `CompletionReuse.Session`）
⇒ 「缓存命中多少」由**上一次调用了什么**决定（单飞信号量只排除并发，排除不了调用序列）
⇒ 同一 prompt 的生成序列随缓存态漂移 ⇒ **判定不可复现**（R426 诚实边界 ① 的 k8 门判翻转）。

**机制取证（传输级，N=5 轮，同一条 gate prompt）**：cache 开 ⇒ `warm/back/mix/mix2` = `197/197/97/197` token（cache_n `226/226/213/226`），
每轮复现同一形态；cache 关 ⇒ `off1/off2/off3` = `180/180/180`（cache_n 恒 0），5/5 轮逐位相同。
⇒ **旧式必红 ∧ 新式必绿**（P1/P2/P3 过）。

**产品级取证（真角色 + 真链，同文重复网格）**：同一条用户消息被问到 r1 门 4 次 ——
改动前 `Pass/Skip/Skip/Skip`（raw_len `148/106/247/102`，判定与文本都不恒定）；改动后 `Skip×4`（`cache_n` 恒 0、`pinned` 1→4），
同配置重复轮仍 `Skip×4`。远端调用 **4 → 2~3**、token **4243 → 2053~2101**（−51.6%）。
归因机检：`alignment_ok=true ∧ attribution_ok=true`（顺序分区 + 回复形态交叉校验）。

**改动**：`LocalGenerationRequest.CacheReuse`（默认 true = 逐位零回归）+ `CompletionProfiles.ReuseFor`（唯一映射点）
+ 门判/判官两处显式 `CacheReuse=false` + `TurnGate.CachePinned`/`LastCachedTokens`、`RelationJudgeCounters.CachePinned`
+ 门判 telemetry `cache_n`/`pinned` + 新测 7 例 + repo skill `decision-path-determinism`。

**诚实边界**：① P4 **未过**——传输级 20 次 cache-on 门判全为 P，未观测到 S/P 翻转 ⇒ 只证「判定**输入**不可复现」（弱宣称）；
② P5c **证伪**——钉死后 raw_len 仍 4 种取值（`113/105/102/100`；重复轮 `128/108/111/113`）⇒ 文本**逐位**复现未达成，
宣称收窄为「判定结论恒定」；③ 本地判官在本配置**未生效**（2/2 `remote_fallback`、45/66 s，被门判占满单飞槽）；
④ 判别力负控落空（k8p 的新诉求消息走「[隔离任务]」旁路，没进 r1 门）⇒ 「钉死后门仍能 Pass」**无证据**；
⑤ 传输级 prompt 由产物代码重建（角色种子等长占位）；⑥ KPI 有轮间抖动（远端调用 2 vs 3）。

**下轮候选**：① 逐位可复现的残余来源（采样档 / 线程归约 / 服务端状态）；② 门与判官的**真隔离**（独立 slot `id_slot` 或独立进程，
本轮只证「关缓存」这一种隔离）；③ 构造能进 r1 门的新诉求网格（补判别力负控）；④ 打点把规则层单列 `rule`。
## R428 · 同文折叠（排序/去重层）：R427 根因判定的产品落地

- **前置因果**: R427 机检坐实「残留并列对 = 同文重复」（位置逐位差 0/335、Jaccard 1.0）⇒ 同文对**任何**打分族恒同分 ⇒ 出口在**排序/去重层**。「换信号族」对该对为伪命题 ⇒ 本轮改的是排序/去重，而非打分。
- **变更集**: `src/agent/session/SessionHistorySearch.cs`（`Hit.CollapsedDuplicates`；`Search` 第 4 步**同文折叠**；`Render` 输出 `同文副本+N`）+ `src/agent.tests/SessionHistorySearchTests.cs`（+6 例）。
- **零参数设计**: 无阈值/权重/开关；折叠条件 = 规范化正文**逐字符相等**；保留者 = 既有全序（score desc → `SessionId` Ordinal asc）首者；折叠数**可见**（字段 + 渲染）。
- **真机成对裁决 = PASS**（C1–C7 + C2b 全绿；判据 T0 冻结于 2026-09-14T10:17:22Z，先于跑测）:

| 语料 | N 臂（pre-fix，sha `2d363b6d132b06e2`） | T 臂（treated，sha `c547b0bec5b8fbf8`） |
|---|---|---|
| A（冻结，含同文对） | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408 → probe-0914125831-p005 0.1408 | cli-6bf6dc8d 0.2798 → probe-0914125816-p004 0.1408（`同文副本+1` on p004） |
| D（不同文同分·负控） | r428-d1 0.2284 → r428-d2 0.2284 | r428-d1 0.2284 → r428-d2 0.2284（无折叠标记） |

- **臂身份自证（C1）**: N 臂读数与 R423 verdict 已落档的 `T_treated\|A` **逐位相同** ⇒ 两臂唯一变量 = 本轮 diff。
- **闭式**: 同文组 `[probe-0914125816-p004, probe-0914125831-p005]` ⇒ 保留者**预测 = 观测 = `probe-0914125816-p004`**（Ordinal 较小）；折叠出 = `probe-0914125831-p005`。
- **不变量**: 全部保留者分数与 N 臂**逐位相同**（含 `cli-6bf6dc8d` 0.2798）；`llm_call` 打点 = 0；每查询恰 1 条 `recall_query`；渲染声明命中数 == 实际命中行数；语料**逐字节未被改动**。
- **诚实边界（不宣称）**: ① 证的是**去重层行为**，不是召回质量提升；② 被折叠会话的 **id 不可见**（只计数为 `同文副本+N`）⇒ 若需 id 级可追溯，须让 `Hit` 携带被折叠 id 列表（本轮刻意不做，避免改渲染契约）；③ 折叠在 `topK` **之前** ⇒ 会改变原可能进入 topK 末位的候选（对「列出全部相关会话 id」类需求是行为变更）；④ 未测：>3 文档的真实长库内存/时延、**近同文**（非逐字符相同）去重、`/recall` 之外的路径。
- **产物**: `eval/capability/r428/{run_r428.py, verdict-r428.json, README-evidence.md, stdout-*}`；计划 `docs/plans/v0.49.0-r428-duplicate-collapse.md`。
- **下轮候选**: ① 被折叠 id 可见化（渲染/打点）；② **近同文**去重（须先过 R427 skill 闸：并列先判同一性 + 可分性预检）；③ R426 遗留首要：门与判官**争用隔离**。

## R427 — 「词袋计数族并列」根因判定：并列对**同文**，且 R423 闭式基线取自呈现精度（零产品改动）

- **靶点**: R423 收口时登记的残留并列对（`p004`/`p005`，`distinct 90/90 ∧ tf(存在) 4/4`）被判为「词袋计数族不可分边界」，并留下「换信号族（语义/位置）」的下轮候选。本轮**先做可分性预检**。
- **判决**: **PREMISE-REFUTED** —— 靶点前提不成立，**不进入实现**（止损一轮）。零构建、零测量、零产品源码改动。
- **F1（承重）**: 该并列对**内容重复** —— 检索正文逐词元相同（位置差 0/335，Jaccard 1.0）⇒ 任何打分族都不可能分开同文文档 ⇒ 「换信号族」对该对为伪命题，正确落点在**排序/去重层**（确定性 tie-break / 同文折叠）。
- **F2（承重）**: R423 的 A 臂闭式基线 = `0.059 × TfSat(4)` **精确等于**其登记值 0.14079136730607356（0.059 是 R422 的两位小数呈现值）；全精度应为 0.14076436276343704（基数 0.05898868348219042）⇒ 该基线属**口径混算**；R423 的比值判据与 B 臂读数不受影响。
- **F3/F4**: 位置族在**构造**样本上可分且零参数闭式一致（ratio 1.46875 精确），但在真实语料**无判定样本**（不存在非同文的并列对）⇒ 增益未证；新边界 = 「同 `distinct` ∧ 同 `tf` ∧ 同 `df` ∧ 同首现相对位置」时位置族亦并列。
- **判据**: P0 口径对齐（pin 精确重现）、P0b 基线溯源精确等式、P1 并列复现、P1b 同文检测、P2 位置族在真实对可分（**FAIL = 发现本身**）、P2b 族非空（fail-closed）、P4 命中集合不变；控制 N1 身份、N3 新边界。全绿除 P2。
- **仪器事故 2 起**: ① 首版 P0 用 5e-7 容差对比**呈现精度**已发布值 ⇒ 假红，修 = 容差按半 ulp + 单列 P0b 精确溯源；② 构造样本用「ASCII 词+空格」⇒ `Normalize` 剥空白致整段粘成单 token，`|d.Tokens|` 3 vs 2 ⇒ 前提不成立，修 = 改 CJK 二元组族 + `synthetic_valid` fail-closed。
- **轮号碰撞（一等事件）**: R426 由并发执行体占用（`eval/rover/r426/budget-{A,B,C,D}-k6-r426b1.json` 17:54–17:58 仍在写入）⇒ 本侧**让号取 R427**，未触碰对侧产物。
- **共享文档破坏（一等事件，已修）**: 本节的写入被并发写入者以「逐字符换行」形态落盘（1,512 行 × 1 字符）⇒ **行级判读全部假阴性**（`grep R427` = 0 而那两行文本其实都在）。修复 = 按「逐字符拼接等同性」机器证明后重排为正常行；⚠️ 后续任何写入 `improvements.md` 的轮次都必须做**行结构检测**（1 字符行连跑即判坏）。
- **产物**: `eval/capability/r427/{precheck_position.py, precheck-r427.json, summarize_r427.py, README-evidence.md, detect_line_explosion.py}`；`docs/plans/v0.48.0-r427-duplicate-tie-precheck.md`。
- **下轮预注册（R428）**: 确定性 tie-break / 同文折叠（排序层），真机成对 AOT；判据 = 同分同文两条命中存在与输入列举顺序无关的全序 ∧ 非同文同分对误折叠 = 0（负控）∧ 命中集合与排序不变量成对机检。

## R426 · 关系判官（CorrectionDetector L2 微判定）本地化 —— 「每轮一次 ~45 tok 远端小调用」清零

- **靶点（用户令 KPI 的直接残余项）**: R425 已证「门跳过主调用」，但**跳过轮仍残留 1 次远端判官调用**（R425 证据里 k8 格 3 次调用**全是**判官）⇒ 本轮的 1 步 = 把该微判定的 caller 换成 r1 本地优先。
- **改动**: `ModelCatalog.cs` 增 `local.relation_judge` 键（默认 false）；`LocalGenerationPort.cs` 增 `RelationLetterJudge.TryNormalize`（**只在闭合 `</think>` 之后的结论区**取独立 C/A/N，截断/无字母 ⇒ 未判定；语言无关纯函数）、`RelationJudgeCounters`；`ModelQueueRouter.cs` 增 `RelationJudgeEnabled`/`JudgeRelationLocalAsync`（预算 512 ≠ 调用方 64/128；失败/未判定/记账违规 ⇒ 返回 null ⇒ 调用方**必须**远端兜底）；`IndustrialAgentV2.cs` 判官 caller 选择 + `correction_judge` 打点（source/kind/letter/ms/tokens/prompt_len/msg_head）。
- **读数（桩侧真值, NS=`-r426b1`, AOT sha `538c4e05…`, IL 警告 0, 单测 23/23）**:

| 臂 | k6 调用/判官/tok | k8 调用/判官/tok |
|---|---|---|
| A 本地关 | 10 / 4 / 14081 | 9 / 3 / 13576 |
| B 门开+judge关（R425 口径） | 6 / 4 / 4725 | 3 / 3 / 166 |
| C 门开+judge本地 | **3 / 1 / 4561** | 2 / 1 / 2586 |
| D 负控（无模型） | 10 / 4 / 14081（≡A） | — |

- **判据**: PASS 12 / PARTIAL 2 / FAIL 2 / UNDECIDABLE 1。token 降幅 A→C = **k6 −67.6% / k8 −81.0%**（≥30% 达标）；判官远端调用 4→1、3→1（PARTIAL：残余是 fail-visible 兜底）；负控 D ≡ A 逐位 ⇒ **增益归因 r1 成立**。
- **反例（必须记）**: k8 格出现**门判翻转**（B 6×Skip → C 5×Skip+1×Pass）⇒ +1 次主链调用（≈2524 tok）**超过**判官省下的量级，该格 token 反高于 R425 臂B（2586 vs 166）⇒ C6/C4 **FAIL**。
- **未测到（不宣称）**: 本地判官 vs **真远端判官**的一致性（对手是桩 ⇒ 恒 Neutral，无判别力，判 UNDECIDABLE）；跨轮 +12 tok（0.09%）漂移不追因。
- **下轮首要候选**: ① 门与判官**争用隔离**（同一 r1 端口下门判不稳，代价远超判官收益）；② 打点修复：规则层命中现被记为 `source=remote`（须单列 `rule` + 兜底原因）；③ `allowed_kinds` snake_case 永不命中的白名单静默失效；④ 本地判官人工金标（C/A/N 各 ≥20 条）。
- **产物**: `eval/rover/r426/{run_arm.sh,run_grid.sh,analyze.py,prov_check.py,stub_openai.py,drive_task.py,analyze.py,c11.json,README-evidence.md,verdicts.json}`；`docs/plans/v0.47.0-r426-relation-judge-localization.md`。
- **轮号**: R426 由本支占用（17:48 占用闸空 ⇒ 起跑 17:54）；并发支已按铁律**让号取 R427**（对侧 `improvements.md` 已登记，本侧不改写对侧产物）。

## R425 — 「非实质轮占比 → 降幅」敏感性网格（零产品改动；判决 **PARTIAL**）

**动机**: R424 把「−30%」报成**单点**（50% 占比 → −33.3% 调用 / −58.5% token）。单点不可外推 ⇒ 本轮把口径改成**曲线**：非实质轮占比 k/8 ∈ {12.5%, 25%, 50%, 75%, 100%}，每格真机 AOT 成对（臂 A = 本地通道关 / 臂 B = 门开 + r1 在），另跑归因臂 B′（门开 + 模型缺）。

| 非实质占比 | 远端调用 A→B | token A→B | token 降幅 | 调用降幅 |
|---|---|---|---|---|
  | 1/8 = 12.5% | 10→9 | 14567→12494 | **14.23%** | 10.00% |
  | 2/8 = 25.0% | 10→8 | 14292→9980 | **30.17%** | 20.00% |
  | 4/8 = 50.0% | 9→5 | 14119→4523 | **67.97%** | 44.44% |
  | 6/8 = 75.0% | 10→6 | 14069→4721 | **66.44%** | 40.00% |
  | 8/8 = 100.0% | 9→3 | 13564→166 | **98.78%** | 66.67% |

- **归因**: 臂 B′（无设备）k=6 = 10 调用 / 14,073 token ≈ 臂 A 10 / 14,069（差 0.028%）⇒ **无 r1 则增益归零 ⇒ 增益归因 r1，而非机械门**。
- **判决 PARTIAL（预注册真红，未事后放宽）**: `C_a` 严格单调被 **k=6 66.44% < k=4 67.97%** 证伪；`C_b`（D_k = k·ĉ）被相对误差 24%/29%/43%/7%（容差 15%）证伪 ⇒ **节省不按轮可加、占比不是充分统计量**；`C_c`/`C_g` 被「跳过轮仍残留一次 ~50 token 小调用、该轮回复仍来自远端桩」证伪 ⇒ 门的跳过是**部分跳过**（省主链、留小调用）。**事后判据**（单列）: A 参照假阴性 **0**；可归因跳过轮 12/12 例降 token（其中 10 例降到 0）。
- **宣称收窄**: 本任务族内 **占比 ≥25%** 时 token 降幅 >30%（25%→30.17% 仅擦线；12.5%→14.23% 不达标）⇒ 用户令「≥30%」的**适用面**是「非实质轮占比 ≳25%」，不外推。
- **与 R424 不可比**: 两轮脚本不同（R424 的 8 轮 / A=12 调用；本轮 A=9–10 调用）⇒ 绝对读数不同源，只在本轮内做网格差分。
- **仪器事故 4 起（都是「读数不可信」类，已入档）**: ① 首跑 batch **漏传 `--role`** ⇒ 门未进判，A/B **逐格逐位相等** + 无本地推理时延；源码坐实 `src/agent/IndustrialAgentV2.cs:1464` 要求 `ActiveRole != null` ⇒ **门相关臂必须显式传 role，否则静默测到未门路径**（该批次保留为阴性对照，不作治疗读数）；② 逐轮调用归属按「首个覆盖窗口」⇒ 窗口重叠把整程调用记到第 1 轮，改**顺序分区**后未归属 0；③ 器具 cleanup 未回收框架自启的 `llama-server` ⇒ 11 只孤儿（r1 一只 1.4 GB，`ppid=systemd`），本轮清理并加 `pkill -P $HOST_PID`，b2 跑后残留 **0**；④ 结算器读 `prov-*.json` 路径写错（字段在 `under_test` 下）⇒ 修读取路径，判据未改。
- **形态**: 两臂同一 AOT 产物 `/tmp/pub_r423/agenthost`（15,168,064 B, sha `2d363b6d…`），`prov_check.py` 跑测前 fail-closed（IL 壳负控 rc=131）；**产品源码零改动** ⇒ 未重发布、未重跑全量测试（表单 13/13）。
## R424 — 主线 KPI 的**发布形态身份**修复 + 在 AOT 上复现（零产品改动）

- **起因（身份不可验证）**: R413 台账记 `agenthost_bytes: 15138848 / aot_il_warnings: 0` 并宣称 AOT 读数，但其器具 `eval/rover/r413/run_arm.sh:12` 的被测路径是 `src/agent.host/bin/Release/net10.0/agenthost` = **78,256 B 的 IL apphost 壳**（同目录并存 `agenthost.dll`；`env -i <bin> --version` ⇒ `You must install .NET…` rc=131）。时序亦不合：臂 A/B 落盘 10:57 / 12:04:44，`publish_aot.sh` 产物 mtime **12:07:16** ⇒ AOT 建在测量之后；全仓无 `publish → bin/Release/net10.0/` 拷贝脚本。⇒ R413 读数是 **JIT 中间证据**，`agenthost_bytes` 属事后另做的构建，不是被测对象身份（措辞守界：**不断言「一定不是 AOT」，断言「形态未验证」**）。
- **动作（一步）**: 在**可自证 AOT 产物**（`/tmp/pub_r423/agenthost`, 15,168,064 B, sha256 `2d363b6d…`, IL/trim 警告 **0**）上重跑**逐字相同**的任务脚本，并把「形态自证 + 成对负控」做成**跑测前 fail-closed 硬闸**（V0）。三臂：A（无 local 段）/ B（门开、模型在）/ **B′（门开、`model_path` 指不存在 ⇒ 无设备负控，兼 r1 归因臂）**。
- **真机读数（外部真值 = 桩侧逐请求落盘）**:

  | 臂 | 远端调用 | 远端 token(估) | 跳过轮 |
  |---|---|---|---|
  | A（分母） | 12 | 16,888 | — |
  | B（r1 门） | **8** | **7,007** | 2/4/6/8 |
  | B′（门开·无设备） | 12 | 16,891 | 0 |

  **C1 −33.3% 调用 / C2 −58.5% token（均 ≥30% ✅）**；C3 零假阴性；C4 跳过轮 = 21 字非 LLM 模板；C5 臂 B′ ≡ 臂 A（差 0.018%）；**C6 省下 4 调用 == 4 个非实质轮，且 B′ 无 r1 ⇒ 增益归零 ⇒ 增益归因 r1 而非机械门**。V0/V1/V2 形态与门真身闸全绿 ⇒ **PASS（9 预注册 + 5 事后）**。
- **与 R413 的关系**: 两臂读数**逐位相同**（12/16,888 · 8/7,007）⇒ **该任务上 JIT 与 AOT 读数不可分**；R413 证据的**本体成立**，本轮补的是**身份**。另：R413 登记字节 15,138,848 与本次 15,168,064 **不同源**。
- **role 额外数据（用户令「记得要挂载 role 的额外数据」）**: 调用点 `src/agent/IndustrialAgentV2.cs:1481` = `ActiveRole.Id + "|" + Clip(ActiveRole.ProfileSeed, 80)`；`TurnGateJudge.BuildPrompt`（`LocalGenerationPort.cs:234`）把它作为 `【角色设定】` 插入本地门提示。**实证非空**：桩侧捕获的远端系统提示内含 `【角色:疑问者】你是一个低调但执着的追问者…`（同 run 同字段）。**边界**：成长经历形参 `null` = **未挂**；且门提示内容不可直接观测（下轮加打点）。
- **仪器缺陷 2 起（都是「读数不可信」类）**: ① 器具跑 IL 而台账宣称 AOT（本轮封堵：`eval/rover/r413/run_arm.sh` 现 fail-closed，实测 `rc=2 [REFUSED]`）；② 逐轮调用归属在轮边界对**异步判官调用**有 ±1 轮滑移（已有 `t_start/t_end`+桩 `ts` 口径；总量精确、未归属 0）。⇒ 已登记为下轮候选。
- **命名空间碰撞（一等事件）**: 与并发执行体撞号 R423（对侧 = 检索 tf 饱和，`eval/capability/r423/`）⇒ **本侧让号至 R424**（17:10:36 迁移 `eval/rover/r423/ → eval/rover/r424/`，计划改名 `v0.45.0-r424-aot-mainline-replication.md`）；R423 归对侧；未改写历史、未删对侧产物。根因：启动占用检查未复跑「活动执行体 + 锁 + 目标轮文件 mtime」全序列。
- **计划/证据/登记**: `docs/plans/v0.45.0-r424-aot-mainline-replication.md`（§3–§5 预注册 17:05:36 < 首臂 17:06:23）；`eval/rover/r424/README-evidence.md`（L4）；`docs/verification-registry.json` → `r424.mainline-token-budget-aot-replication`；回归抽查 **47/47**（`--filter FullyQualifiedName~TurnGate`）。
- **下轮候选**: ① 形态闸下沉/统一（标 r413 为历史器具）；② 成长经历块**有界挂载**对假阴/假阳的影响（须成对负控）；③ **占比敏感性网格**（1/8、2/8、4/8、6/8）把 −30% 口径表述为「占比 → 降幅」曲线，替代单点宣称；④ 本地门提示打点（`local_gate_prompt_len`）使挂载可机检。

---

## R423 — 跨会话检索打分：**词元频次饱和** + 可分性预检（R422 §5 预注册项落地）

**版本**: R423 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **判决**: **PASS**（主判据 10/10 绿；含边界登记与两起仪器/流程事故入档）
**主题**: R422 收窄宣称后遗留的「等长文档残差并列」。靶点按 R422 §5 预注册 = 词元频次（tf）信号。

- **★ 可分性预检（先做，且据其结果改写靶点）**: 对 R422 残留并列对取**机检**特征向量（真实存储 Load + 文档构建 + 真实分词器）⇒ 两份长文档 `distinct 90/90 ∧ tf(存在) 4/4` **逐项相等** ⇒ 频次信号对该对**恒为空操作**（数学上恒零，不是"效果有限"）。⇒ 该并列登记为**词袋计数信号族的不可分边界**（需换信号族：语义/位置），本轮**不**作"R422 残留零区分度已消除"的全称宣称，只宣称「等长**但出现次数不同**的文档可分档」。
- **改动**: `SessionHistorySearch.cs:98` 打分分子 `Idf(t) * TfSat(tf)`，`:219` `TfSat(int tf) => 1.0 + Math.Log(tf < 1 ? 1 : tf)`（**因子 ≥1 ⇒ 分数符号不变 ⇒ 命中集合可证不变**；单调不减 ∧ 对数饱和=相对增益递减）；`:203` `CountTokens`，`:75-76` 词元集由计数键派生（**单一真源**，无二次分词口径分叉）。零参数/零配置/零 LLM。
- **判据（预注册，harness 先写后跑）**: C0 语料目录条目集纯净 / C1 六查询命中集两臂逐元素相同 / C2 负控全等 ∧ 治疗分档 / C3 比值 == `1+ln3`（闭式）/ C4 tf=1 逐位不变 ∧ tf=4 == 登记值×`(1+ln4)` ∧ 隐含 tf == 机检钉死值 / C4b 负控读数 == R422 登记值 / C5 极性不退化 / C6 渲染可机读+零 LLM / C7 语料逐字节且只读 → **全绿**；C8（等长同频次仍并列）**单列边界登记**。
- **读数（AOT 成对真机）**: T `/tmp/pub_r423/agenthost`（15,168,064 B，**IL/trim 警告 0**，sha `2d363b6d132b`）vs N `/tmp/pub_r422/agenthost`（sha `55e1ed1a5d45`）。等长可区分对（`|d|=2`，tf 3 vs 1）: N `[0.4901, 0.4901]` **全等**（臂身份自证）→ T `[1.0286, 0.4901]` **分档**，比值 `2.098755` vs 闭式 `2.098612`（相对误差 6.8e-5），隐含 tf `3.000`。R422 冻结语料: tf=1 文档 `0.2798` **逐位不变**（因子单位元）；tf=4 文档 `0.059 → 0.1408 == 登记值×(1+ln4)`（隐含 tf `4.0006`）。
- **★ 首跑预测输入纠错（已归档）**: `verdict-r423-run1-predictor-error.json` 保留 C4 **红** —— 红因是**预测输入人工复算错**（只读 `LongTermMemory` 段 ⇒ tf 算成 2，真值 4），实现行为符合闭式（隐含 tf 实测 4.000）。处置: 预检数字改**机检钉死**（单测 `R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted`）+ 新增"隐含 tf == 钉死值"子判据；**判据结构与阈值未改**（不放宽、不为变绿而动实现）。
- **★ 语料目录污染事故（C0 由来）**: `eval/capability/r422/fixture-sessions/sessions/` 空子目录 —— 存储构造即 `Directory.CreateDirectory(<path>/sessions)`（`SessionMemoryStore.cs:19-20`），某次以**语料目录本身**作根构造就地建出。三份语料 sha256 **未变**（== R421 登记），`rmdir` 清除；harness 加固为只取文件 + 新增 C0（条目集纯净机检）。
- **单测/形式校验**: `SessionHistorySearchTests` **26/26**；形式校验（VerificationForm|SkillGeneralization|DevPlanDocRef）**10/10**。
- **登记**: `r423.recall-tf-saturation`(L4)；计划 `docs/plans/v0.44.0-r423-tf-saturation.md`；证据 `eval/capability/r423/{verdict-r423.json,README-evidence.md}`；台账 `eval/capability/kpi.jsonl`。
- **流程教训（语言无关，已抽为 skill）**: ①改进排序/打分类信号的**第一步是对已知并列样本做可分性预检**（信号在该对取值相等 ⇒ 改进恒为空操作 ⇒ 换族或登记边界，别投入实现）；②**预检/预测数字一律机检取值**，人工复算会漏口径（本轮 tf 手算 2 vs 真值 4，被闭式对账当场逮住）；③闭式对账（`比值 == 1+ln tf`）比"看起来分了档"强得多。
- **诚实边界**: ①频次因子对「词元数与出现次数皆相同」者无区分度（不可分边界）；②收益面未量化（真实语料中该形态占比未知）；③`(1+ln tf)` 无参数口径**未做**变体网格/上界 oracle ⇒ 不宣称该靶点最优（BM25 `k1/b` 族未探）；④「整串命中兜底/加成」两条路径不带频次因子（常量赋值），口径局部不一致未评估；⑤`|d|` 仍取去重词元数（R422 §6-2 遗留未做 A/B）。

---

## R422 — 跨会话检索打分校准：**文档长度归一**（R421 §5 预注册项落地）

**版本**: R422 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **判决**: PASS 之外 **PARTIAL**
**主题**: R421 真机暴露的 **打分零区分度**（`/recall 存在` 命中 3 份文档、分数**全等** `0.5596`）——短文与长文并列，排序退化为 sessionId 字典序。本轮按 R421 §5 **预注册靶点**落地文档长度归一。

- **改动**: `src/agent/session/SessionHistorySearch.cs:97-99` —— `score /= Math.Sqrt(qSet.Count) * Math.Sqrt(Math.Max(1, d.Tokens.Count));`（余弦式；**零参数/无语料均值/不改确定性**；除数为正 ⇒ 分数**符号不变** ⇒ 命中集合可证不变）。单测 +2（`SessionHistorySearchTests.cs:322-359`）：词元数 1/3/5 ⇒ 分数**严格递减**；真机语料族上「归一在作用」∧「R421 极性不变量未被破坏」**同时**成立（成对，防一刀切）。
- **判据（预注册：harness 先写后跑，未被结果回改）**: B1 命中集逐元素不变 / B2 分数不再并列 / B3 负控臂全等（臂身份自证）/ B4 极性不退化 / B5 数值对账 / B6 渲染可机读 / B7 零 LLM / B8 语料逐字节且只读。
- **读数（AOT 成对真机）**: T `/tmp/pub_r422/agenthost`（15,159,856 B，**IL/trim 警告 0**）`[0.2798, 0.0590, 0.0590]` vs N `/tmp/pub_r421_pre/agenthost` `[0.5596 ×3]`；对账 `|d|_est=[4.0, 89.96, 89.96]` ⇒ `0.5596/√4=0.2798` ✓、`0.5596/√90=0.0590` ✓（F4 渲染，相对容差 2%）。命中集**逐元素相同**（B1 绿）。
- **★ 预注册判据被证伪（本轮核心诚实项）**: **B2 红** —— 3 份命中里两份**词元数相同**（≈90）⇒ **任何仅依赖文档长度**的归一在数学上都不可能为其分档（残差并列是应然，不是缺陷）；**B5 红** 因容差 0.02 与 **F4 渲染精度**不匹配（事后按 2% 相对容差重算为绿）。⇒ 宣称**收窄**为 `claim_scope`：「分数与文档词元数成反比、召回集合不变；**等长文档仍并列**（后续候选：tf/语义信号）」，**不**作「零区分度已消除」的全称宣称。
- **登记**: `r422.recall-length-norm`(L4, 带 scope 注记 + 预注册失败项如实列出)；`verdict-r422.json` 保留 `pre_registered_failures=[B2,B5]` 与 `checks_posthoc`（事后判据**不与主判据混列**）。
- **附带修复（同血缘召回面，独立登记）**: `src/agent.rag/RAGConfig.cs:706-719`（修前）词袋 embedding = `Math.Abs(word.GetHashCode())`（**进程随机化** ⇒ 同一文档跨进程向量不同 = 落盘索引重启不可复现）+ `(hash + seed * 31337) % dimension`（**可溢出为负** ⇒ `embedding[负]` ⇒ `IndexOutOfRangeException`，栈 `GenerateEmbedding ← IndexAsync`）。取证 = **9 进程样本：红 2 / 绿 7**（概率性 ~20%/进程；量级自证 700 文档 × ~20 token ⇒ 每进程期望溢出 0.2 次）+ **基线对照**（stash 本轮源码后重跑 1176/0/0）证明红与本轮改动无关。修 = FNV-1a 确定性哈希 + **无符号**取模（`RAGRecall.StableHash`/`BucketOf` + `InternalsVisibleTo`）；判据 = **确定性等价类** 4 例（负控：旧公式在该边界输入**确实产负下标 -15** ∧ 新式恒 [0,128)；对抗性 hash 恒非负；与测试侧**独立实现**的 FNV-1a 逐元素相等；端到端词袋召回命中）。**通则**：概率性缺陷不得以「重跑变绿」为判据。
- **诚实边界**: ①`|d|` 只做「词元数」单口径，未 A/B；②事后 2% 容差**不得当主判据复用**；③3 份语料不足以估「等长并列」的实际影响面。

---

## R421 — 跨会话检索**否定极性**：`¬存在 ≠ 存在`（R420 真机缺陷闭合）

**版本**: R421 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）· **回填标注**: 本节由 `docs/plans/v0.42.0-r421-polarity.md` + `eval/capability/r421/verdict-r421.json` 重建，**读数未改**。
**主题**: R420 真机暴露「`存在`(2 字) 与 `不存在`(3 字) 命中**同一批**文档、分数同为 `1.5660`」⇒ 用户问「X 不存在吗」会收到「关于 X 的文档」，读起来像**肯定**。机理 = CJK 二元组「不存在」包含「存在」⇒ 词面子串重叠被当成同一命题。

- **改动**: `SessionHistorySearch.Tokenize` 对**否定标记**（不/没/未/无/五）自身及**紧邻的 1 个二元组**加 `NegMark`(U+0001) 前缀 —— `Normalize` 丢弃全部控制字符 ⇒ 真实文本不可能产出该前缀 ⇒ **无碰撞**；查询侧与文档侧走**同一** `Tokenize`（**无查询侧特判**）。
- **判据/读数**: 四查询真机成对（T=`/tmp/pub_r421` vs N=`/tmp/pub_r420_pre`）：`不存在` 命中 **3 → 0**，且 N 臂 `不存在` 与 `存在` 命中集**逐元素相同**（缺陷复现）；`存在` 两臂命中集一致（**召回未被打死**）；`llm_call=0`、`recall_query=1`/查询；表单 13/13。
- **排除项（已登记）**: ①否定在句中且距命中词 **>1 字**的作用域扩展；②**打分长度归一** —— 已由 R422 接手（首项仍在册）。

---

## R420 — backlog L2 待办① / L7-G1：跨会话检索**接线**（`SessionHistorySearch` 生产消费点从 0 到 1）

**版本**: R420 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: `SessionHistorySearch` 于 R370 交付并带 10/10 单测，但**生产消费点为 0**（`grep` 仅命中测试）——"库面实现 + 单测齐" ≠ "已接线"（本仓 ⑧ 类缺口，L7-G1 高优先级）。本轮按循环 branch A 取**最前**未完成计划项，只推进一步：接上唯一合法出口。

- **改动（四表接线，缺一即静默送 LLM）**：① `Known` 白名单 `+= "/recall"`；② `TryRoute` switch 臂返回 `Handled/Command/Argument`；③ 宿主 dispatch 特判（解析 `[topK]` 默认 5 夹取 1–50 → `SessionHistorySearch.StoreSource(_sessionMemoryStore)` → 渲染；**通道级**打点 `recall_query{query_len,topk,hits}`）；④ 新增**可测**静态 `Render(...)`，空命中出显式「无命中」文案（不静默空白）。
- **判据（预注册，C4 ∧ C5 才成立）**：C1–C3 单测 **28/28 PASS**（`/recall` 三元断言 + `KnownCommands` **全集行为探测**（漏臂即红）+ 3 条渲染断言）；C4 真机治疗臂同窗口 `recall_query`=**3** ∧ `llm_call`=**0**；C5 负控臂 = **接线前 AOT 产物**（`/tmp/pub_r414/agenthost`，12:19）同形输入 `recall_query`=**0** ∧ `llm_call`=**1** 且 stdout 无渲染、直接送 LLM。
- **仪器教训（本轮关键）**：CLI 在 `-q` 下**恒定**打印「意图分析/管线执行」⇒ 只读 stdout 会把两条臂都判成"走了主链"，结论**完全相反**。行为类读数一律取通道级打点；"本地指令零 LLM"必须配**接线前产物负控**才不是恒真断言（与 R415「判别力需成对断言」同族）。
- **登记表**：新增 `r420.recall-command-wiring`(L4)；改写前先断言「序列化器逐字节复现原文件」= True 后才程序化插入（diff = 19+/1−，无整份重排），登记表改动后**当轮**跑形式校验。
- **★ 新缺陷（真机暴露，未修，下轮候选）**：打分对**否定**无感 —— `存在`(2 字) 与 `不存在`(3 字) 命中**同一批**文档、分数同为 **1.5660**；`外星词根zzq不存在` 得 2 命中 ⇒ 用户问「X 不存在吗」会收到「关于 X 的文档」，读起来像**肯定**。机理 = 词面子串重叠 + 无否定处理 + 无分数门。与 skill「标记『出现』≠『误用』」同族：**词面重叠 ≠ 语义相关**。
- **诚实边界**：①负控为**产物级**（非源码回滚）；②真机 7 条查询单批单机，只作行为证据、**不构成召回率**；③两条正向查询（`会话记忆`/`向量召回 嵌入`）0 命中 = 语料分布问题（探针题面占据），不与"召回全灭"混同。

---

## R419 — 探针多轮化：把「轮数 / 首次通过率」从恒等判据变成可分化判据（回填）

**版本**: R419 · **日期**: 2026-09-14 · **状态**: 已收口（仪器侧达成；真机读数为**负结论**，如实登记）· **回填标注**: 本节由 `docs/plans/v0.40.0-r419-probe-multiturn.md` + 提交 `695d6ba`/`77a49bc`/`98339a8`/`05b8c94` 重建，**读数未改**。

- **因果链**: R418 已把「过程/成本」维度落成仪器（`eval/probe/process_metrics.py`），但探针只有单轮 ⇒ 「轮数恒为 1」「首次通过率 ≡ 整题全对率」两个维度结构性不可分化。
- **交付**: 探针多轮化仪器（成对正负控 + 7 态自证）；三个**仪器缺陷**闸：① 被测程序打印坏字节 ⇒ 判定器 `UnicodeDecodeError` 崩掉整臂（改字节捕获 + `errors="replace"` + `bad_encoding` 计数，`grade selftest` 29→31）；② **同命名空间重跑静默覆盖**既有读数 ⇒ `REFUSE_NS_COLLISION` 闸；③ 首轮失败在日志不可见 + `reply_chars` 恒 0（归档 11.9 KB 而摘要写 0）⇒ 首轮行原样打印 + 集中回填（`run_probe` 25→26）。
- **真机读数（诚实结论）**: 4 次 `onfail` 跑 **3 次饱和 / 1 次分化** ⇒ 真机侧**未稳定复现分化**，本轮不作能力结论；决定性微实验 PASS（同 sid 跨进程 4271 命中）。
- **口径坑入档**: `turn N` 是**进程内**轮次标记 ⇒ 轮数须取**归档文件数**（外部真值）。
- **证据**: `docs/plans/v0.40.0-r419-probe-multiturn.md`、提交 `05b8c94`（收口）/`98339a8`（§4-§5 落地）/`77a49bc`（微实验）/`695d6ba`（起步存档）。

## R418 — 探针「过程/成本」维度 KPI：归属铁律 + 真机成本读数 + 成对负控（回填）

**版本**: R418 · **日期**: 2026-09-14 · **状态**: 已收口（仪器 + 真机读数 + 登记齐；本地提交未推）· **回填标注**: 本节由 `docs/plans/v0.39.0-r418-process-kpi.md` + 提交 `737a45d`/`1f44c8b` 重建，**读数未改**。

- **因果链**: R417 处理掉题集天花板（饱和）后，仍有分辨力的维度是**过程/成本**（每题 tokens / 轮数 / 首次通过率）⇒ 需独立仪器与归属规则。
- **交付**: `eval/probe/process_metrics.py`（过程/成本维度 KPI 仪器）+ **归属三级降级**（精确名 → 时间窗 `[ts-elapsed-5s, ts+60s]` 内唯一候选 → `n/a` + 记因；**绝不任取第一个候选**）。
- **成对负控**: 歧义/缺失样本必须落 `n/a`，且 **`n/a` 从均值分母剔除并单列计数**（`n/a ≠ 0`）——把缺读数按 0 摊会让「每题成本」假降。
- **诚实边界**: 该轮成本读数取自单轮题集 ⇒ 「轮数」维度此时仍退化为恒等判据（由 R419 处理）。
- **证据**: `docs/plans/v0.39.0-r418-process-kpi.md`（§3 实现结果 / §4 复验命令）、`eval/probe/process_metrics.py`、提交 `1f44c8b`。

## R417 — 探针反饱和：3 个高判别力族 + 族级缺陷注入负控（回填）

**版本**: R417 · **日期**: 2026-09-14 · **状态**: 已收口（判别力自证 PASS；**首个非饱和真机读数**）· **回填标注**: 本节由 `docs/plans/v0.38.0-r417-probe-anti-saturation.md` + `eval/rover/r417/README-evidence.md` + 提交 `0488017` 重建，**读数未改**。

- **因果链**: 原 7 族题集对当前链**已饱和**（agent 与 oracle 同为整题全对 1.0；同题复跑 seed 20260913 = 35/35）⇒ 天花板效应，「质量」无法从它读出 ⇒ 靶点是**判别力**，不是题量。
- **交付**: 新增 3 个高判别力族 `topo_min`/`vm_run`/`json_mini` + `tight_gen` **每题强制「规格紧」隐藏用例** + **族级缺陷注入负控**（作弊/缺陷解必须整题全对 0，oracle 正控满分）。
- **真机读数**: 整题全对 **1/3**、用例级 **47/54**（诚实登记：真机**仍饱和**，只有 JSON 族打成非饱和）。
- **两处判定器真缺陷（测量层，已修 + 已配负控）**: ① 长回复里「报告式」候选片段顶掉完整可编译程序 ⇒ 候选提取分两轮 + 前缀长度下限；② `exit≠0` 顶掉正确 stdout ⇒ 分类改 **stdout 优先**（期望为空时崩溃仍判失败）。
- **机检/登记**: `eval/probe/grade.py --selftest` **29/29**；全量 **1164/0/0**；形式校验 6/6；登记 `docs/verification-registry.json` → `r417.probe-anti-saturation`（L4）。
- **证据**: `eval/rover/r417/README-evidence.md`、`docs/plans/v0.38.0-r417-probe-anti-saturation.md`、提交 `0488017`。

## R416 — R371-D2 收口：发布产物自包含 config 的**仓库外 cwd 真机验收**（能力自检循环）

**版本**: R416 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: D2（发布产物不自带 config）的 csproj 复制规则此前已落地，但「自包含」从未从**仓库外 cwd** 真机取证。本轮按能力自检循环 branch A 只推进一步：把该断言升级为可复现的外部真值。

- **harness（不改产品代码）** `eval/rover/r371d2/`：`run_d2_acceptance.sh` 三臂（治疗 / 撤销修复负控 / 修复前产物负控）+ `verdict.py`（6 断言三态裁决，臂缺失或超范围走**弃权**不判红）+ `append_kpi.py`（幂等台账，重跑不污染趋势）。
- **判据（预注册，全外部真值）**：治疗臂（`/tmp/pub_d2/agenthost`，cwd=`/tmp/d2-cwd`，`env -u AGENTFRAMEWORK_CONFIG`）stdout **不得**含「模型目录为空」，**且**必须出现**越过选模**的证据；两路负控**必现**该症状——合取成立才判过。
- **读数**：`verdict-r371d2.json = pass`（6/6）。治疗臂 `rc=0 / 849 B`：输出「prompt 构建完成 ~3385 tokens」并点名 `deepseek-flash` ⇒ 已解析**自带** config 完成选模，失败点后移到凭据未设（**非**配置缺失）；撤销修复负控（移走自带 config）与修复前产物负控**都命中**「模型目录为空」⇒ 断言非恒过。静态自证：cwd 及其 8 级祖先无 config；自带 config 与仓库 config 同源（sha 一致）。
- **登记表**：新增 `r416.release-selfcontained-config`（L4）。等级依据 = **运行期行为 + 两路负控**（注入缺陷必失败），**非** AOT 编译校验——已按 `aot_check_policy=release_tag_only` 在该行写入口径澄清。登记表改动后**当轮**跑形式校验两次：**13/13 PASS**。
- **诚实边界**：①三臂退出码均为 0 ⇒ 该失败**不以退出码体现**，判据只认 stdout 外部真值；②凭据未设，未做真实远端调用（不影响本判据）；③本轮发现**并发兄弟作业**（tag `r416` 探针跑测 12:52:50–12:53:11，仓库外 AOT `/tmp/pub_r414`，读数 35/35 `validity=ok`）——其被测二进制在仓库外，故 build 替换类污染不适用，但其**时间类分量**按指示性看待；轮号 R416 由两支共用，命名段已区分（`eval/rover/r371d2` vs `eval/rover/r416` + `data/probe/*-r416-*`）。

## R415 — 链级钉死「前置门入参 = 用户本轮原文」：把 R413 的防线从源码级升级为行为级（外部真值）

**版本**: R415 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: R413 的前置门增益曾因「门吃 `prompt.UserMessage` 而非 `message.Content`」归零；
当时唯一防线是 G29 **扫源码字面量**，挡不住等价回退。本轮补一条**行为级、端到端**的钉死。

- **harness（不改产品代码）** `eval/rover/r415/`：本地后端换成**确定性假实现**（模拟 llama-server 的
  `/health /props /apply-template /tokenize /completion`；待判原文含「谢谢」⇒ S 否则 P），
  链侧全真：真 `agenthost --frontend-api` + 真 DI 装配 + 真 `ModelQueueRouter` + 真 `LlamaCppLocalGenerationPort` + 真进程/HTTP（零 P/Invoke）。
- **判别力构造**：知识提示型技能 `skills/r415-gate-pin/SKILL.md`（`type: knowledge_hint`，关键词 `收到/谢谢`）
  命中后其 body 作为 `[技能知识参考]` 尾挂到 `prompt.UserMessage`（`IndustrialAgentV2.cs:1200`）
  ⇒ 该轮 `prompt.UserMessage != message.Content` ⇒ 门若吃错变量立刻可辨。
- **判据（预注册，全外部真值）**：A3 判别请求**不含**哨兵 + A7 远端请求**确实含**哨兵/参考块 —— 两者合起来才构成判别力；
  单看「判别请求含原文」没有判别力（`prompt.UserMessage` 本就包含原文）。
- **读数**：`verdict-r415.json = PASS`，**22 项断言 × 2 形态（JIT/AOT）全通过**。
  判别请求 3 次（文本 385/385/387 字符，哨兵 0 / 参考块 0 / 技能块 0）；远端正控 t2 哨兵 1 + 参考块 3、t3 哨兵 2 + 参考块 5；
  跳过轮回复 21 字（本地模板）≠ 桩罐头，P 轮 = 桩罐头 ⇒ 跳过真实、不静默、**假阴性 0**；
  负控臂 `off`（本地通道关）本地请求 0 / `/apply-template` 0，同一轮本就会走远端。
- **仪器教训（两次无效跑，已入档）**：① 假服务端必须显式解 `Transfer-Encoding: chunked`，否则请求体读成空
  ⇒ 判定恒 P、判据全废；② 判定规则必须锚定「待判原文」段（`【用户消息】` 到 `答案:`），
  全文匹配会命中判别提示词自带的 few-shot 示例（示例里就有 `收到，谢谢。 → S`）⇒ 三轮全判 S。
  两条都是**测量仪器缺陷**而非产品缺陷；无 A7 正控时，仪器错与「门吃错变量」无法区分。
- **边界**：假后端只证明**接线/机制**，不给任何自然分布比率（三轮不是分布）；增益本身仍以 R413 的真 r1 读数为准；
  微步骤/探索回注路径的追加块本轮未构造（仍只有源码级覆盖）；AOT 形态为**补充证据**（registry 口径：AOT 仅发布 tag 构成登记依据）。

## R414 — R371 断链真机验收（D7 优先）+ 失败可见性缺陷闭合：`Success=false` 的降级文案不再被链侧丢弃

**版本**: R414 · **日期**: 2026-09-14 · **状态**: 已实施（本地 commit，**未推**）
**主题**: backlog 最前未完成项 = R371 修复串的真机验收读数；验收过程抓到真缺陷并同轮闭合。

- **验收（真机 E2E，`eval/rover/r371d7/`，4 臂 24 项断言 ⇒ `verdict-r371d7.json = PASS`）**：真进程 `agenthost --frontend-api` + 确定性远端桩（逐请求落盘=外部真值）。
  - D7 截断续写：`llm_call_continue before=102 added=58 after=144 recovered=true`，`after` 与**独立复刻**合并长度逐位相同（overlap=16）；`tail_before` = 断点原文；救回后结构闭合。
  - D1 空正文恢复：`first_content_len=0 / first_reasoning_len=400 ⇒ recovered=true`。
  - **负控**：完整正文臂 ⇒ 远端 2 请求 / 恢复遥测 0（无病不治）。
- **★ 真缺陷（本轮抓到并修复）**: `src/agent/IndustrialAgentV2.cs:1604`（修复前）`if (!llmResponse.Success) response.Content = string.Empty;`
  ⇒ D1 在「重试后仍空」时写入的**面向用户降级文案被丢弃**，用户看到空白（真机 `empty_always` 轮 1 `reply_len=0`，`loop_turn.reply_chars=0`）。
  既有单测只在 **router 层**断言文案非空 ⇒ 链侧丢弃测不到（「有实现 ≠ 已接线」）。
- **落地（最小契约位，非布尔打补丁）**: `QueueResponse.ContentIsUserFacing` / `LLMResponse.ContentIsUserFacing`（默认 false = 零回归）+ `ModelQueueAdapter` 透传
  + 链侧 `UserFacingFailureContent(...)`裁定：**只透出被显式标记的内容**（未标记 ⇒ 仍为空，原始报错正文不外泄）+ `Success=false` 语义不变。
  可见降级文案不再拼接 `ex.Message`（内部信息卫生；原文保留在 `Error`）。
- **回归**: `UserFacingFailureTests` 5/5（含 2 条源级钉死）；修复后 4 臂重跑 `ok/empty/truncate` 读数逐位不变，仅 `empty_always` 轮 1 `reply_len 0→66`（修复前对照文件在库）。
- **口径澄清（审计须知）**: `llm_call.truncated` 反映**最终**正文闭合性（救回后为 false），截断事实只在 `llm_call_continue`；`added_len` = 续写原文长度（去重前）。
- **诚实边界**: 桩驱动 ⇒ 证明机制而非自然分布截断率；`empty_always` 为构造病态分布；单机单次读数。

## R413 — r1 本地真假判别接进链管道（端口化）：机械 Pass 前置 + 非 LLM 模板 ack ⇒ 一轮总 token ↓58.5% / 远端调用 ↓33.3%（判过）

**版本**: R413 · **日期**: 2026-09-14 · **状态**: 判过（C1–C4 全 PASS；本地 commit，**未推**）
**主题**: 用户钦定「利用 r1 对真假信息判别（挂载 role 额外数据，管道已接），让用户一轮任务总 token 显著下降 ≥30%（主要是不必要的 LLM API 请求少了）」。

- **落地（端口化，非硬接线）**: `ILocalGenerationPort`（`src/agent.modelqueue/LocalGenerationPort.cs`）+ `LlamaCppLocalGenerationPort`（`src/agent.llamacpp/`，进程 + HTTP，零 P/Invoke）；DI 接线 `ServiceCollectionExtensions.cs`；`ModelQueueRouter` 本地优先分支 —— 端口缺失 ⇒ 判据必拒 ⇒ **全走远端 = 零回归**；`TurnGateJudge`（机械前置门 + 结论区解析 + `ThinkOpen`/`ThinkClose` 常量）。
- **前置门 v2（本轮定，取代 v1 纯 r1 判别）**: ① 机械 Pass 前置（问号/疑问词、指令/新诉求、纠正/失败词、结构化实体、长文本 ⇒ **直接 Pass，不问 r1**）；② 仅无信号短消息交 r1（二元 S/P、192 token 上限、只读思考块之后的结论区）；③ 被跳过轮回复 = **非 LLM 模板**（`LocalSkipFallback`），不再让 r1 生成（v1 实测会复读前文并反问）。
- **判据读数（外部真值 = 桩侧逐请求落盘 + 驱动器观测；臂 A = 本地通道关 / 臂 B = 开）**:
  臂 A **12 调用 / 16,888 token**；臂 B **8 调用 / 7,007 token** ⇒ 调用 **-33.3%**、token **-58.5%**（阈值 30%）。
  门遥测（臂 B 7 轮到达推理段）：机械 Pass 3（轮1/3/5）+ r1 判别 4（轮2/4/6/8 全 Skip）；逐轮回复：轮2/4/6/8 = 模板（门消化），轮1/3/5 = 远端应答，轮7 = 链侧澄清拦截（两臂同现，与门无关）。
  **结算 `eval/rover/r413/verdict.py` → `verdict-r413.json`：C1 PASS · C2 PASS · C3 PASS（实质轮零误跳）· C4 PASS（跳过集恰好 = 预注册寒暄集、回复均为模板）⇒ 判过。**
- **前置门 v1（上轮）读数与换方案理由**: v1 达 -86.7% token / -50% 调用，**但判不通过** —— 负控抓 2 例误跳（新诉求「另外，测试命令呢？」、纠正语「不对，你上一条回答不准确…」）+ ack 退化 ⇒ 换「机械前置 + 模板 ack」。
- **本轮两处空心根因（真机诊断，均已修 + 已回归）**:
  ① **判的不是用户原文而是 `prompt.UserMessage`** —— 该字段已被 role 块/计划续跑/微提示追加（R379 Fix A）⇒ 机械门恒 Pass、增益归零；诊断法 = 先补 `local_turn_gate_config` 一次性遥测，把「门有没有开」变成可观测；修 = 判 `message.Content` + **G29 源级回归**（钉死链侧入参）。
  ② **源码写入通道把尖括号字面量替换成 tokenizer 形态**（思考块结束标记 → 码点 `0x3c,0xff5c,end,0x2581,of,0x2581,thinking,0xff5c,0x3e`）⇒ 解析器恒搜不到 = 空心降级（看着在判、全降级）；修 = 公开常量 `ThinkOpen`/`ThinkClose`（字符码构造）+ G24/G25 回归（含真机原文）。
- **机检**: `LocalTurnGateTests` **46/46**（含 G24 真机原文、G25 常量形态、G29 链侧入参源级钉死）；全量 **1158 / 0 / 0**（`TEST_EXIT=0`）。
- **AOT（发布形态验收）**: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r413` ⇒ `PUBLISH_EXIT=0`、**IL 警告 0**、`agenthost` **15,138,848 B**（R412: 15,093,088 B）。
- **诚实边界**: ① 单轮脚本 / 单模型（r1-distill-1.5b-q4km）/ 单机单次读数，脚本参数化可重跑；② 机械信号表是**穷举白名单**，表未覆盖的短消息仍交 r1（本次 4 条寒暄全对，样本量小，**不构成 r1 可靠性证据**）；③ 桩侧逐轮归属受「后续轮 prompt 含历史文本」干扰 ⇒ 只作参考，判据只用外部计数 + 驱动器观测；④ 轮7 的 0 主调用是链侧澄清拦截、非门行为；⑤ 本轮改动**未推送**（推送暂停令在位）。
- **证据**: `eval/rover/r413/{verdict.py,verdict-r413.json,budget-A.json,budget-B.json,calls-A.jsonl,calls-B.jsonl,turns-B.jsonl,probe-struct.jsonl,run-B/data/telemetry/host.jsonl}`、`docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md`（§7.3–§7.6）。

---

## R412 — 多会话 slot 争用：单 slot 不踢缓存（三臂逐位相同）+ 会话级账本（分母不互相污染）

**版本**: R412 · **日期**: 2026-09-14 · **状态**: 已落地（代码/文档/登记见本次提交）
**主题**: R410 下轮候选 ②「多会话并发 slot 争用下的复用率」；R411 计划 §7 明确留 R412 的同一 regime。

- **先修前提（仪器校验）**: 冒烟阶段臂无判别力（两会话共享超长公共子序列 ⇒ A/B/C 读数相同）⇒ 改用**互不相同**的两份长文档前缀（`prefix-p1/p2.txt`，4336 / 4316 token），并用 `/apply-template` + `/tokenize` **独立量公共前缀**: LCP=0/1、最长公共片段 16 token ⇒ 有判别力。判据修订记录在计划文档 §2.1（**跑之前**写死，非跑后调参）。
- **服务端 regime 实测**（独立实现直连 HTTP，不经过产品代码；`-np 1`、`-c 4608 -b 512`、f32 KV、flash-attn off）: 三臂 A 同会话连续 / B 两会话交替 / C 真并发（线程同发）+ 第四臂 D（`-np 2 -c 9216`，每 slot 4608）⇒ 携带复用率**四臂逐位相同**（S1 0.9998 / S2 0.9991）；冷启 `prompt_ms` 148.3 s / 155.8 s vs 热轮 0.84 s ⇒ **真实 KV 命中**（非计数器假象）。⇒ **单 slot 不互相踢缓存**，K2b 双条件（≥97% ∧ ≥4224）在多会话形态下成立。
- **产品侧缺陷（代码事实钉死，与上面结论独立）**: `LlamaCppTextGenerator` 旧 ceiling 取**实例级** `LastPromptTokens/LastGeneratedTokens`，而长驻端口是进程内单例 ⇒ 多会话交替/并发时 A 读到的「上一轮」可能是 B 的 ⇒ 台账分母 `carryOverCeiling` 被污染（判红/判绿都可能失真且外部看不出）。修复 = 新增 `LocalSessionTracker`（按 `sessionKey` 分桶；无键退回实例级 = **零回归**）+ 端口暴露 `Sessions` 计数。
- **判据 J1a–J1h（含负控）**: 分桶（反例: 实例级会给 408）/ 首轮 0 / 无键兜底且不建桶 / 并发计数与租约归零 / **纯串行不得报争用**（`MaxConcurrentTurns==1 ∧ ConcurrentTurns==0`）/ 有界 / 夹紧 / 接线。单测 8 例。
- **诚实边界**: ① 仅 n=2 会话（同机单 server）；② `-np 1 -c 4608` 实测 server RSS **2.39 GB**（本机 3.66 GB）⇒ 更大 n 或更长前缀受内存约束，**未测**；③ 前缀中段截断点分布（R410 候选 ③）仍未测；④ 墙钟不作判据（只报单次形态）。
- **登记**: registry 新行 `llamacpp.session-ledger`（`updated_round=R412`）；TaskPlan 节点 `dev-multi-session-slot`；计划文档 `docs/plans/v0.34.0-r412-multi-session-slot-contention.md`；证据 `eval/rover/r412/`。
- **下轮候选（R413）**: ① **接产品链路**：本地生成（r1/llama.cpp 长驻端口）作为**链管道精炼计划节点**接入 `ModelQueueRouter` 通道选择（可替换执行面端口 + 数值对账 + 被使用计数 + 无设备负控）—— **与 R351 无关**（R351 只移除旧的「本地 LLM 使用」路径；用户 2026-09-14 纠正 R412 报告里的误读）；② N>2 会话与内存上限下的复用；③ 前缀中段截断点分布；④ 微内核 A/B（15× 悬案）；⑤ R402–R407 台账回填。

## R411 — 长驻生成端口 + 本地 K2b 台账：「口径必须靠独立实现对账钉死」+ 双条件判据

**版本**: R411 · **日期**: 2026-09-14 · **状态**: 已落地（代码/文档/登记见本次提交）

**用户令（逐字）**：「继续下一轮」

**完成记录**：
- **补上 R410 缺的第三条件**：新增长驻生成端口 `LlamaCppTextGenerator`（懒启动 + 单飞 + 跨调用保活同一 `llama-server`）。E2E（单进程 3 轮）逐轮 `ProcessStarts=1`，命中 **0 → 4352 → 4385**，携带复用率 **0.9998**，整体复用率 **0.9959**，前缀 **4337 ≥ 4224** ⇒ K2b 达标形态首次在产品侧复现（exit 0）。
- **负控（判据是活的）**：19 token 前缀会话 ⇒ 复用率 0.963、绝对长度不达标 ⇒ **判越线，exit 7**，诊断点名「前缀绝对长度 19 token（需 ≥4224）」；无 turns 的请求 ⇒ 用法错 **exit 2**（首跑曾是 core dump exit 134，已修）。
- **★ 口径教训（本轮最重要）**：按字段名把 `tokens_evaluated` 当成「新评估数」是错的 —— **它就是 prompt 总长**（`timings.prompt_n` 才是新评估数，`tokens_evaluated == prompt_n + cache_n`）。错算导致总长虚增（530 → 1042）、出现 **有效命中率 1.0302 > 1（物理不可能）** 与随后的假越线。独立实现（`/apply-template` + `/tokenize` + `/completion` 三方对账）把它钉死；**「比率 > 1」= 口径错的可机检特征**，已写成单测。
- **本地分母不套远端经验界**：远端 provider 的「需要命中的部分」含 64-token 单元打折（mt_fix4 规律），而 llama.cpp 的 KV 缓存连上一轮**生成**的 token 一起持有 ⇒ 本地台账用「可复用上限 = 上一轮总长 + 上一轮生成」，命中超出上限时**弃权**（记 `-1` + `Abstained`，不硬套判决）；命中未上报时**不判红**（缺失 ≠ 错误）。
- **判据 = 合取**：携带复用率 ≥97% **∧** 前缀绝对长度 ≥4224（沿用 R410「比值不是 KPI」）。单测 11 例（台账 7 + 口径 4，含「口径错 ⇒ 比率 > 1」与「比值达标/长度不足」两个负控分支）。
- **判据机检**：`eval/rover/r411/verify.py` **12/12 通过**；全量 **1087 / 0 / 0（34 s）**；登记表 **46 行**（新行 `llamacpp.session.long_lived_generation`）、TaskPlan **18 节点**、形式校验 **9/9**。
- **自错披露**：① 口径换算错（见上）；② 把 R410 的 780 字符前缀当成「4249 token」（4249 是探针运行时重复 25 次的产物）⇒ 首跑正负例结论颠倒；③ 预注册判据 N1 写错（预言「比值达标」，实测比值也不达标），**修正判据并另立单测覆盖该分支**，不为让脚本变绿而放宽；④ 会话分支曾在 `try` 之外 ⇒ 异常逃逸 core dump；⑤ STJ 默认大小写敏感 ⇒ 小写 `turns` 反序列化成空。

**诚实边界**：单 slot 顺序两会话、只测 497/4337 两点、3 轮 n=1 形态；多会话并发争用未测；**产品主链路未接**（`ModelQueueAdapter` 仍走远端）；正例前缀是合成重复文本（4337 token），真实 system/skills 前缀能否天然 ≥4224 未验证；助手轮回放的逐字节一致性未单独取证（本轮复用近全量，但无字节级对照）；墙钟不作判据。

---

## R410 — 会话长前缀复用（K2b 落点）：「比值不是 KPI」+ 宿主生命周期缺口 + 生成口径分离

**版本**: R410 · **日期**: 2026-09-14 · **状态**: 已落地（代码 `8263ac8`；文档/登记见本提交）

**用户令（逐字）**：「继续下轮」

**完成记录**：
- **实测（判据先预注册）**：同一 server 内，4255 token 长前缀第二次请求只重算 **5 token**（`cache_n=4250`，复用率 **0.9988 ≥ 0.97**，墙钟 233.9 s → 0.5 s）；负控（前缀首 token 改变）归零；`cache_prompt=false` 恒 0。
- **关键结论：比值不是 KPI，绝对长度才是** —— 短独立 prompt 的「复用比」0.94 看似不低，但绝对可复用只有 **17 token** ⇒ 对 K2b 红线（≥4224）覆盖 **0.402%**，结构上不可能达标。只看比值会得出相反结论。
- **宿主生命周期缺口（实测，非推断）**：同样 `--reuse on` + 稳定 487 token 前缀，两次 CLI 调用 `CachedTokens` **都是 0**、`SessionCacheMisses=1` —— 每次调用新起 server（新 KV 缓存）⇒ 跨进程复用 **0%**。⇒ **K2b 达标三条件：长驻 server + 稳定长前缀 + cache 开；缺「长驻」时另两条都白搭**。
- **代码**：`CompletionReuse {Session, Reconciliation}`（`GenerateAsync` 默认 Session = 生产口径）；`CompletionProfiles.Build()` 收敛为「口径 → 参数」唯一映射点；`CompletionResult.CachedTokens`（服务端 `cache_n`，非估算）；`SessionReuseCalls`/`ReconciliationCalls`/`SessionCacheMisses`（静默失效可见化）；CLI 新增 `--reuse on|off` 与 `--system-file`（会话长前缀入口）。
- **测试**：新增 `CompletionReuseTests` **4/4**；全量 **1076 / 0 / 0**（R409 基线 1072 + 4）。
- **顺带修掉两个真缺陷**（均由全量回归暴露、非本轮引入，同属「拿墙钟当闸门」类）：① `SessionPerformanceTests` 的墙钟 3x 比值断言 ⇒ 改为「等价性作判据、计时只作信息」；② `LlmServiceStatusTests` 的 5 s 固定就绪截止 ⇒ 放宽到 30 s 并把实测等待写进失败信息。两者在争用下都产生假红（单独复跑全绿）。
- **登记**：`docs/verification-registry.json` 新行 `llamacpp.session.prefix_reuse`（L4，45 行，`updated_round=R410`）；TaskPlan 节点 `dev-session-prefix-reuse`；计划文档 `docs/plans/v0.32.0-r410-session-prefix-reuse.md`；证据 `eval/rover/r410/`。

**自错披露**：① 探针 v1 成本估小（单线程 prefill 实测 26 t/s ⇒ 4807 token 一遍 185 s）且只在末尾落盘 ⇒ 被掐断后零证据，v2 才改成分臂增量落盘；② 「会话内复用 99.88%」与「跨进程复用 0%」两条曾混在同一结论里，补跑 CLI 后才分清。

**基线**：全量 1076/0/0；本地生成 17.9 t/s（llama.cpp 不变）；K2b 会话内顺序复用 **0.9988**（达标）/ 跨进程 **0**（缺口）。

**下轮候选（R411）**：① 产品侧长驻 provider 接线（嵌入侧已是 `AddSingleton`，生成侧待接）；② 多会话并发 slot 争用下的复用率；③ 前缀中段变化的截断点分布；④ 微内核 A/B（15× 悬案）；⑤ R402–R407 台账回填。

## R409 — 本地 prompt 模板闸门（结构性阻断手拼）+「权威 prompt」BOS 口径修正

**版本**: R409 · **日期**: 2026-09-14 · **状态**: 已落地（工作区，待 commit）

**用户令（逐字）**：「继续下轮」

**完成记录**：
- **实测（判据先预注册，后改代码）**：模板来源对账 —— GGUF 内嵌 jinja（走 `POST /apply-template`）与归档 `eval/rover/tokref/r1_chat_template.jinja` 在 **3/3 消息形状逐字节一致**（diff 0 B）⇒ K2b 模板来源漂移风险关闭。
- **BOS 归属裁决（真缺陷）**：96 B 字面权串 + 默认 tokenization（`add_special=true`）= **18 token / 双 BOS**；规范形式 = 渲染串（67 B）+ tokenizer 自动 BOS = **17 token / 单 BOS**，两者 token 流等价（`IdsEquivalent=true`）。产品通路实测：`literal` 18 vs `chat_template` 17，**生成 24 id 逐位相同** ⇒ R408 对账结论不受影响；双 BOS 的实际代价是 **+1 prompt token** 与**两通路前缀不可复用**（K2/K2b）。
- **闸门落地**：新端口 `ILocalPromptRenderer`（唯一实现经 `/apply-template` 由**模型元数据**渲染 ⇒ 调用方物理上无法手拼）；`LocalPromptGate` 四规则（来源非模型元数据 / 空产物 / 字面含 BOS / 以 EOS 结尾 ⇒ 全判红）；`GenerateAsync` 只收结构化 messages；字面通路降级为 `CompleteLiteralPromptAsync`（显式诊断用 + 计数）；被使用计数 `TemplateRenders` / `PromptGateRejections`。
- **规则按实测修正**：初版「不得包含 EOS」会**误拦合法多轮**（118 B 含 EOS 轮分隔符、不以 EOS 结尾）⇒ 改为「不得以 EOS 结尾」。
- **机器验证**：`agenthost --llamacpp --verify-template`（退出码 6 = 未通过）⇒ `Verdict=gated_single_bos`、`RenderedBosCount=1`、`LiteralBosCount=2`、`IdsEquivalent=true`、exit 0。
- **测试**：新增 `LlamaCppPromptGateTests` **9/9**（sha 锚点钉死 + 5 项注入缺陷负控 + 2 项防误拦反向控制）；全量回归 **1072/0/0**。
- **AOT**：规范命令复跑 **exit 0 / 0 IL 警告 / 14,950,608 B**（政策 `release_tag_only` ⇒ 仅参考证据）。
- **登记**：`docs/verification-registry.json` +`llamacpp.prompt.template_gate`（L4，44 行）；TaskPlan 节点 `dev-local-prompt-template-gate`；计划 `docs/plans/v0.31.0-r409-local-prompt-template-gate.md`；证据 `eval/rover/r409/`。

**自错披露（3 处）**：① 首轮把 `2081`（字符）与 `2237`（UTF-8 字节）当成两个模板的长度，误报「差 156 B」（单位错）；② 闸门初版 EOS 规则会误拦合法多轮输入；③ R409 探针脚本内建裁决行问错对象（比较了 `96B/add_special=true`）故打印 False —— 正确等价对由 `--verify-template` 独立确认。

**基线**：R408 全量 1063/0 ⇒ R409 全量 **1072/0/0**；本地生成 17.9 t/s（llama.cpp，与 R408 持平）。
**台账缺口（遗留）**：R402–R407 未回填本台账，其证据在 `eval/rover/r40x/` 与 `docs/plans/v0.2x-r40x-*.md`。 **R518 机检更正（2026-09-17）**：机检实测缺口为 R402 / R404 / R405 / R406 / R407（R403 有节但**错位**、R408–R416 在位）⇒ 已逐节回填 + 修正 R403 排序；机检器 `eval/capability/r518/scan_round_sections.py`（C1 覆盖 + C2 分区序，rc 0/1/2）。**本行前半段口径（R409 时登记）自本行更正起作废**。

## R408 — 本地 GGUF 引擎整线退役，产品线全面切 llama.cpp（进程 + HTTP，零 P/Invoke）

**版本**: R408 · **日期**: 2026-09-14 · **状态**: 已落地（commit `b00917c`，本地未推）

**用户令（逐字）**：「去掉所有关于gguf的本地代码开发，完全改用llama.cpp」+「不用对比自研的了，直接用llama」

**完成记录**：
- **退役范围**：`src/agent.rover/{gguf,quant,infer,runtime,token,cli}/` + `src/agent.embedcpu/` 整工程删除（10.3k+0.6k LOC）；`formal/` + `gpu/spirv/` 保留（非 GGUF 内核）；`agent.rover` 不再产出可执行文件。
- **接入形态**：`src/agent.llamacpp/`（Host / Client / Provider / TextEmbedder）只走「进程 + HTTP」，全仓 `DllImport`/`LibraryImport` **0 命中**。依据：跨平台（Windows 无 `AddressFamily.Unix`）+ R90 实测 LLamaSharp native interop 在 NativeAOT 下 SIGSEGV。
- **两进程形态**：生成与嵌入互斥（`/v1/embeddings` 需 `--embeddings` 启动）。
- **读数**：生成 24/24 token id 与 llama-cli 基线逐位相同（dev 17.891 / AOT 17.64 t/s，`IdsMatch=true`）；嵌入 768 维 L2 归一，命令路径与 DI 路径指纹一致（`sha256=d5336321…`），新旧向量 `cos=0.1586`。全量回归 **1063/0/0**；AOT 0 IL 警告。
- **登记表**：3 行引擎对账行改写为 `llamacpp.process.boundary` / `llamacpp.embedding.port` / `engine.retired.no_local_gguf`。
- 口径修正（R409 追认）：R408 所用「96 B 权威 prompt」字面含 BOS，在默认 tokenization 下会双 BOS（18 token）；规范形式为渲染串 + 自动 BOS（17 token）。生成结果 24/24 不受影响。

**基线**：退役前 1130/2/1132 ⇒ 退役后 **1063/0/0**。

## R407 — qwen2 前向对账：attn bias 层归属缺陷（定位 + 修复 + 逐位验证）（回填）

**版本**: R407 · **日期**: 2026-09-14 · **状态**: 已完成（V1–V6 全部真实读数；AOT 发布与全量回归已跑）· **回填标注**: 本节由 `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md` + 提交 `cd8feeb` 重建，**读数未改**。

- **因果链**: R406 把 chat template 升为「读 GGUF 模板 + Jinja 子集解释器」并 32/32 逐字节对齐 ⇒ 乱码**归因移出模板侧**；本轮把「引擎缺陷」推进到**具体张量与具体层**。
- **缺陷**: `ForwardPass` 把 **`blk.0` 的 attn bias 喂给全部 28 层**（qwen2 每层 bias 逐字节不同）⇒ 静默数值错误（不报错、只降质量）。
- **修法/验证**: 按层取 bias + 独立实现逐位对账（V1–V6）。
- **证据**: `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md`、`eval/rover/r407/`、提交 `cd8feeb`（**R403–R407 工作区一并提交** ⇒ 该提交同时承载 R405/R406 产物）。

## R406 — 模板驱动 chat template（Jinja 子集）与 R1 链归因（回填）

**版本**: R406 · **日期**: 2026-09-14 · **状态**: 已完成（P0-2a 解释器 / P0-2b 生成路径接线）；P0-1（llama.cpp oracle 收尾）进行中 · **回填标注**: 本节由 `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md` + 提交 `cd8feeb` 重建，**读数未改**；**无独立证据目录**（如实标注）。

- **因果链**: chat template 原为「只为 DeepSeek 手写的专用渲染器」⇒ 换模型即失真。
- **交付**: 从 GGUF 读 `tokenizer.chat_template` 原文 + **Jinja 子集解释器**；以 jinja2 3.1.6 渲染的三套金标夹具（32 例）做**逐字节**对账；生成路径切到模型自带模板。
- **用途**: 用「prompt 已证明正确」这一事实，把 R1-Distill-1.5B 的乱码输出**归因从模板侧移出**（⇒ 交 R407 定位到引擎 attn bias 层归属）。
- **证据**: `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md`、提交 `cd8feeb`（与 R403/R405/R407 同批提交）。

## R405 — 本机增强 R1-Distill-1.5B 计划（四条线，不改权重）（回填）

**版本**: R405 · **日期**: 2026-09-14 · **状态**: 计划已登记；P0/P1 待执行（P0-1 对账在后台）· **回填标注**: 本节由 `docs/plans/v0.27.0-r405-r1-local-enhancement.md` + 提交 `cd8feeb` 重建，**读数未改**；**未见该轮收口节**（状态按计划文档原文登记，不补写读数）。

- **用户令（逐字）**: 「请给我适合本机增强R1-Distill-1.5B的可落地方案」。
- **上游**: R400 生成链（`9d2191a`）+ R403（RoPE 配对修复）+ R404（bge 融合对账）。
- **形态**: §0 先列**本机硬约束**（实测值 + 出处，方案不许绕过它们）⇒ 四条线均不改权重。
- **证据**: `docs/plans/v0.27.0-r405-r1-local-enhancement.md`、`eval/rover/r405/`。

## R404 — bge 融合对账 + 产品口径订正（回填）

**版本**: R404 · **日期**: 2026-09-14 · **状态**: 已完成（对账产物落盘 + 口径订正）· **回填标注**: 本节由 `eval/bge/r404/` 产物 + 提交 `4d1bf90`/`8094faf` 重建，**读数未改**；**无独立轮志文档**（如实标注，证据目录为 `eval/bge/r404/`）。

- **对账产物**: `eval/bge/r404/parity-probe.json`、`eval/bge/r404/csharp-fusion-replay.json`（C# 侧融合重放；`4d1bf90` 刷新产物时**指标全同、仅时间戳变化**）。
- **口径订正（`8094faf`）**: 产品 `lex+small` 融合值为 **0.7833**（**非** 0.8500）+ 110 MB base 删除登记 + 默认模型路径指向链上真身。
- **归属备注**: 该产物目录此后被 `cddcabe`（R516）触碰 ⇒ 归属以提交为准。
- **证据**: `eval/bge/r404/parity-probe.json`、`eval/bge/r404/csharp-fusion-replay.json`、提交 `4d1bf90`/`8094faf`。

## R403 — chat template 裁定：自研 Jinja 子集随 R408 退役 + 工具调用模板「无对象可验」（负控证明探针有判别力）

**版本**: R403 · **日期**: 2026-09-14 · **状态**: 关闭（裁定 + 待触发能力登记；**无代码改动**）
**主题**: backlog R403 的唯一待判项「工具调用模板是否改口径为验证 llama.cpp tool 模板行为」。

- **读数（两臂 + 判别力负控，一条命令 `python3 eval/rover/r403/probe_tool_template.py`）**:
  default 臂（GGUF 自带模板，`--jinja`）= `caps.supports_tools=false` / `caps.supports_tool_calls=false` /
  模板源 `tools` 变量 **0** 个 / `/apply-template` ±tools **逐字节相同**（md5 `b89299b3…`，24 B）/ completions ±tools
  `prompt_tokens` **4 → 4（Δ=0）**，HTTP 200 无报错；
  control 臂（合成 258 B 全 ASCII 模板，`--chat-template-file`）= `supports_tools=true` / ±tools **md5 不同**（29 B vs 62 B）/
  `prompt_tokens` **7 → 18（+11）** ⇒ **负控过关 = 探针有判别力**，default 的「相同」是真读数而非探针盲区。
- **排除替代解释**: `/apply-template` 在 control 臂读到 tools 并改变产物 ⇒ 端点确实转发 tools；default 臂的相同输出来自**模板**（无工具定义位），不是端点不支持 tools。
- **产品侧消费方**: `grep -rn -E 'tool_choice|ToolCall|tool_calls|"tools"' src/ --include=*.cs` ⇒ **0 命中**（零消费方）。
- **裁定**: **R403 关闭**。① 自研 Jinja 子集扩展的对象随 R408 退役（R409 已证渲染归引擎、调用方无法手拼）；② 工具调用模板**无对象可验**（引擎自报不支持 ∧ 模板零工具位 ∧ 产品零消费方，三方一致）。
  「工具调用」转**待触发能力**，准入判据三条**全绿**才开工：(a) `caps.supports_tools == true`；(b) 同 messages ±tools 的 `prompt_tokens` 有差（**不得只看 HTTP 200**）；(c) 产品侧存在发出 tools 的调用点。
- **诚实边界**: 仅现役模型 `r1-distill-qwen-1.5b-q4km` + 本机 build `b1-4df29be` 的单次读数；负控模板是**合成**的，只证探针判别力，不证任何真实模型支持工具调用；工具调用**出参解析**（`tool_calls` → OpenAI 格式）**未测**，属 (a) 之后的独立课题。
- **证据**: `eval/rover/r403/tool-template-behavior.json`、`eval/rover/r403/probe_tool_template.py`、`docs/reports/r403/chat-template-tool-scope.md`。
- **运行纪律入档（两次同族事故）**: ① 测量前清掉 6 个 R412/R413 遗留长驻 server（pid 230833/230849/232136/232152/233614/233632，RSS 合计 ≈3.5 GB，本机共 3.66 GB）⇒ `MemAvailable` 1.14 GB → 2.99 GB；
  ② `pgrep -f "[4]1999"` **仍自杀**（同一命令行的 `curl …:41999` 含裸端口号）——括号技巧只保护**模式字面量**，不保护同一命令行**别处**出现的目标串（同族：`ps | grep "[l]lama-server"` 被自己的 `echo "no llama-server running"` 命中）⇒ 正解 = 被测进程自落 pid，或同进程内 Popen + `killpg` 收尾。

## R402 — rover 生成链性能归因：盘读 vs 计算（三通道取证）+ 读数补登记（回填）

**版本**: R402 · **日期**: 2026-09-14 · **状态**: 已收口（步1 归因 + 步2 读数补登记）· **回填标注**: 本节由 `docs/reports/r402/io-attribution.md` + `eval/rover/r402/` + 提交 `33baddd`/`6483721` 重建，**读数未改**。

- **因果链**: R400 生成链的耗时主体是「盘读」还是「计算」未分离 ⇒ 优化靶点无法选择。
- **交付**: `scripts/r402_io_attribution.py` 三通道取证（进程 IO 记账 `ProcIo.cs` / `ReadBenchCli.cs` 读基准 / 前向通道）+ `docs/reports/r402/io-attribution.md`；登记表 +22 行。
- **步2 结论**: **加线程不升级**（读数补登记于 `6483721`）⇒ 该方向不再投入。
- **证据**: `docs/reports/r402/io-attribution.md`、`eval/rover/r402/{README.md,io-attribution-run3.json,io-attribution-run2-doublecounted-device.json,run1-console-capture.txt}`、`scripts/r402_io_attribution.py`、`src/agent.rover/runtime/ProcIo.cs`、`src/agent.tests/RoverProcIoTests.cs`。

## R401 — 能力自检循环常驻化（用户令：R400 后一直执行 + 60 分钟检测机制）

**版本**: R401 · **日期**: 2026-09-14 · **状态**: 已落地（常驻）

**用户令（逐字）**：「我发现你再R399后就没有遵照之前的安排 继续 进行 【参照当前上下文（非本agent项目的) 并使用本agent和py开发随机程序和解开随机数学难题用于本agent能力自检和总结通用性skill放入skills文件夹内】 这轮R400结束后 请一直执行该任务 （全部任务完成后再次执行，需要检测机制）」

**完成记录**：
- **循环本体** `scripts/capability_cycle.py`（853 行，stdlib）：`status`（检测机制入口，判 `tasks|selfcheck`）/ `emit`（按 seed 生成一轮随机题：6 程序家族 + 8 数学家族）/ `grade`（机械判定：数学=独立暴力 oracle；程序=隐藏用例族 + 失败分类）/ `selftest`（判定力负控）。
- **检测机制**：cron `10f9d6454575` 每 60 分钟跑 `status` ⇒ `tasks` 推进最前计划项一步；`selfcheck` 跑随机程序+数学题自检并沉淀通用性 skill。
- **判定器自检实测 SOUND**：参考解全绿（merge_intervals 16/16、roman_canonical 27/27、ttl_cache 4/4、数学 8 家族 19/19 与暴力 oracle 一致）；**8 个变异解全部必红**且红在预期判据上。
- **本轮真跑（cycle-20260914-s20260914）**：数学=生成树计数 **21**（矩阵树定理 ≡ C(8,5) 子集枚举 ≡ 判定器 oracle，三方一致）；程序=TtlCache **4/4**。读数落 `eval/capability/kpi.jsonl`。
- **通用性 skill**：`skills/spec-uniqueness-and-judge-soundness/SKILL.md`（type=knowledge_hint）—— 判据口径唯一化 + 判定器自检（参考解/变异解/反例成族/场景参数泛化）；过 `SkillGeneralizationTests`（全目录遍历）10/10 + 产品侧 `SkillPackageLoader` 4/4。

**本轮由自检抓出的真缺陷（3 处，全部已修并固化进 skill）**：
1. 「严格解码」写成「贪心消费恰好耗尽」—— **不充分**（非规范写法同样耗尽）⇒ 参考解与题面自相矛盾；改为互逆判据。
2. LRU「最近使用」用 `now` 值当次序 —— 时间戳相等时次序不确定 ⇒ 正确解不唯一；改为访问先后序号（内部自增），并用「时间戳全相等」用例逼出该语义。
3. 判定场景把 `capacity=2` 写死且该判定面无参考解 ⇒ 缺陷躲过自检；改为参数泛化生成 + 每个判定面都有参考解覆盖。

**基线**：R400 全量回归 1088/1088；本轮新增 0 条 C# 测试（循环本体为 py 侧自检设施），门禁 10/10 + 4/4。

## R398 — 随机化能力自检探针 + 通用性 skill 沉淀（exp14 长期线首轮）

**日期**: 2026-09-13 · **状态**: 完成（M1–M5 落地；M6 题集加硬列下轮）· **计划**: `docs/plans/v0.24.0-exp14-random-probe-selfcheck.md`

**用户令（逐字）**: 「使用本agent和py开发随机程序和解开随机数学难题用于本agent能力自检和总结通用性skill放入skills文件夹内」（长期任务，须纳入文档）。

**完成**:
- **随机题集生成器** `eval/probe/tasks.py`（627 行）：程序 6 族（括号修复/矩阵螺旋/最大子段/区间和/CSV 聚合/去重计数）+ 数学 5 族（组合取模/行列式取模/二次剩余解数/期望值/最长递增子列）；每题**双路径验算**，两条独立路径不一致 ⇒ **拒绝发题**。
- **判定器** `eval/probe/grade.py`（300 行）：隔离目录 + 超时 + `-I -B` 沙箱执行；**只认隐藏用例**；失败模式分类；**判定器自身反向负控**（比对函数打坏后必须转红）。
- **编排器 + 真机适配器** `eval/probe/run_probe.py`（380 行）：`oracle` / `file:` / `command:` / `agent`（真机走 AOT `agenthost -q`，py 插件落盘产物）；回复原文落档 `data/probe/replies/`。
- **真机自检跑通**：6 题 21 用例 **21/21 = 1.0000（73.33s）**，失败模式 `{ok:21}`，6 族全 1.0。
- **经验抽象 → skill**：`skills/independent-verification-before-claim/SKILL.md`（语言无关，`type: knowledge_hint`）。
- **门禁扩面**：`SkillGeneralizationTests` 从"只体检 1 个 skill"改为**遍历全部 `knowledge_hint` skill**（加载 / keywords+regex_patterns 非空 / 正文零语言特性 / 负控），当场暴露 2 处存量裂缝并修复：`image-gen` 零 `regex_patterns`（匹配器永不触发）、`critic-rules` 正文含语言 token（语言映射外置到 `references/lang-mapping.md`）。

**关键因果链（判定口径）**: 真机首轮 p001 报 `no_code`（0/6）→ 查回复原文发现 agent **已产出正确程序**（`py_57906c9279782c29.py`，`py_compile` ✓、run exit=0），根因是判定器只认围栏代码块，而产品真实交付 = **CLI 回复区裸代码 + 落盘产物** → 改为多路候选 + 取最长可编译前缀 → 同一回复重判 **6/6**。教训：**判定口径假设错 = 反向的空心指标**（会把满分记成 0 分）。

**负控总数**: 生成器 21/21 + 判定器 13/13 + 编排器 11/11，全部含"打坏判据必须转红"的反向控制。

**诚实边界**: ① 样本 6 题且 100% ⇒ **饱和、零区分度**，对能力提升不敏感，M6 必须加硬；② 数学只判最终答案，不判推理链；③ 沙箱**不是安全边界**（不禁网）；④ 单次读数含模型侧波动，须同题成对比较。

## R397 — DCR 单一口径重算(FAVA 语义) + 口径敏感度实测量化(30.34pp)

**用户令**: 续轮（"继续下轮"）· 承接 R396 附带解锁的 FAVA 正文取证。

**因果链**: R388 起本仓 DCR **双口径并列**(弃权计合规 **145/145=100.00%** / 保守 **101/145=69.66%**), "是否达到 90.5%±5pp"因此**不可断言** —— 100% 与 69.66% 分落区间上/下, 达标与否"完全取决于弃权是否计合规"。R396 把 FAVA 正文里的口径取到 (公式/无弃权项/fail-closed/单一二元矩阵) ⇒ 阻塞解除, 但**按该单一口径重算未做** ⇒ 本轮即补这一刀。

**完成记录**:
- **口径定稿**: `DCR = (TP+TN)/(TP+TN+FP+FN)`, **无弃权项**, 非 `Proceed` 一律 **fail-closed 记 block**(期望侧 `Proceed` ⇒ allow, 其余 ⇒ block; 实际侧同理)。
- **单一口径结果**: **DCR = 145/145 = 100.00%**; 混淆矩阵 **TP=94 · TN=51 · FP=0 · FN=0**; 六类 category 逐类 DCR 全 1.0000。
- **口径敏感度实测(本轮关键产出)**: 同一份数据三种读法 —— fail-closed **100.00%** / 仅可决断集(101 条) **100.00%** / 弃权与畸形按放行 **69.66%** ⇒ **跨度 30.34 pp**。⇒ **"±5pp 裕度"此前不成立的根因是口径自由度本身(30.34pp ≫ 5pp), 不是测量噪声**; 口径现已钉死, 该自由度消除。
- **跨实现交叉对账 4/4**: 单一口径重算器只从 C# 侧报表(`scripts/kpi_dcr.py` 产出)**独立计数**抽数对账 —— `N=145` ✓ / `Proceed == TN == 51` ✓ / `可决断集 == Proceed+Violation == 101` ✓ / `弃权+畸形 == N−可决断 == 44` ✓(符合"跨实现对账换独立实现"铁律, 不 import 内核代码)。
- **负控 7/7**(`dcr_align.py --selftest`): 含**解析 oracle**(400 次洗牌 DCR 均值 ≈ `(51²+94²)/145² = 0.5440`)、单点翻转 **Δ=1/145**、常量分类器基线(**全 allow 35.17% / 全 block 64.83%**)⇒ 100% 的信息量全在"同时拿到 51 allow + 94 block"。
- **自捕 2 缺陷(已修)**: ① 自检计数写死 `6` 而实际 7 条 ⇒ 恒 rc=1("闸门自己恒假"的镜像缺陷); ② 敏感度表混用原始处置与二元值 ⇒ 崩(均被一轮 selftest 抓出)。
- **文档收口(禁再"双口径并列")**: 本节 + `eval/dcr/README.md`(口径定稿注 + 清单加 `dcr_align.py`)、`docs/verification-registry.json`(`dcr.harness` 行)、`docs/plans/v0.23.0-exp12-*`(§S4 / §口径纪律)、R388 诚实边界段均改为**单一口径 + 敏感性**。
- 机读产物 `docs/reports/dcr/dcr-single-metric.json`; 报告 `docs/reports/r397/r397-dcr-single-metric-recompute.md`。

**诚实边界**: ① **题集饱和** —— 145/145、FP=FN=0 ⇒ 该数字对能力提升**零灵敏度**, 加硬用例(长轨迹/语义降层)是"达标断言"的唯一前置; ② **与 FAVA 90.5% 不可比**(801 例 aggregate × 三基准 × 含自然语言→IR 降层损失, 本仓 145 例受限片段、零 LLM、无降层)⇒ **"DCR=100%"≠"达到 90.5%±5pp"**; ③ 标签独立性有限(62/145 构造定义; 83/145 z3 推导, 但 z3 与内核共享整数语义 ⇒ 共同盲区不可自发现); ④ 口径映射是本轮工程裁定(可审可改, 改则数字变)。

**基线**: 纯 Python + 文档轮 ⇒ **零 C# 改动**; 全量测试基线不变。

---

## R396 — 产品侧 Vulkan 端口(去 Silk.NET 依赖, 名字/版本与 Silk.NET 逐字一致)

**用户令 (逐字)**: "不要引入silk.net; 但用的vulkan.dll文件名与版本请和silk.net库一致。"

**因果链**: 上轮遗留"产品侧进程内选 vulkan 需引 Silk.NET ⇒ 6 条第三方 IL 告警 ⇒ 待用户决策"; 本轮裁决 = **要能力不要依赖** ——
Vulkan 只需 BCL 的 `NativeLibrary` + 函数指针即可自载, 第三方绑定并非必需; 但"自载"必须证明**与 Silk.NET 用的是同一个加载器**,
否则就是另一套东西 (名字/soname/请求版本任一处不同 ⇒ 行为可能分叉)。

**落地**: 新增 `src/agent.gpu` (零外部包依赖 / 零反射 / AOT)。名字与版本**取证自包内程序集**, 不是读文档:
`eval/vulkan/extract_silknet_loader_names.py` 机械提取 UTF-16 字面量 → oracle (`vulkan-1.dll` / `libvulkan.so.1` / `libvulkan.so` / `libvulkan.dylib`, 源 sha256 落档);
请求版本与引擎侧 Silk.NET 路径 (`Vk.MakeVersion(1,1,0)`) 源码级锁定。

**真机证据**:
- 机检 **5/5** (`VulkanLoaderParityTests`): 名字逐字对账 + sha256 溯源 + 版本反漂移 + **依赖声明投影检查**(不引 Silk.NET: 注释不算、声明算) + 负控 + 真机设备 + 池化复用。
- **JIT 与 AOT 同一结论**: AOT 单文件 1.19 MB, **IL 警告 0**, 输出目录无任何托管依赖; `probe` 输出 `vkdevice{name="llvmpipe (LLVM 20.1.2, 256 bits)" api=1.4.318 vendor=0x10005 type=cpu}`。
- **跨实现对账 SOUND**: 与系统 `vulkaninfo` 逐字段比对 **6/6 一致** (设备名/apiVersion/driverVersion/vendorID/deviceID/deviceType), 对 AOT 产物复跑仍 SOUND ⇒ 自写绑定与独立实现等价。
- 负控 `probe --negctl` ⇒ `not_found` 显式失败 (不静默回退 CPU)。

**诚实边界**: ① 本轮只打通"加载器/实例/设备枚举"(Stage 1+2), **产品侧计算管线 (descriptor/pipeline/命令缓冲) 仍是引擎侧实现**, Stage 3 待做; ② 内存堆解析 (结构对齐) 未做, 只断言对账过的字段; ③ 本机唯一设备是 **lavapipe 软件 ICD** (显示设备为 QEMU 模拟 Cirrus GD 5446), **真 GPU 斜率需外部机器**, 复跑脚本已备; ④ oracle 溯源依赖本机 nuget 缓存, 缺失时显式 warn 而非静默。

**报告**: `docs/reports/r396/r396-product-side-vulkan-loader-parity.md`。

**附带解锁 (⑤ dcr-align)**: FAVA 正文 (arXiv `2607.27267v1`) 已抓到并落盘, DCR 口径取得权威原文 ——
`DCR = (TP+TN)/(TP+TN+FP+FN)`, **无"弃权"项**, 不确定一律 **fail-closed 记 block**; aggregate = **单一二元矩阵**(非各集宏平均);
trace-conditioned 100.0% 论文自陈为 *labeled diagnostic*, 须与 zero-shot 主表分开读; 论文**未给方差/置信区间** ⇒ ±5pp 仍是本仓自设工程裕度。
由此解释本仓"合规 100.00% / 保守 69.66%"两面不矛盾(弃权处置不同); 对齐重算(=fail-closed 归并后单一口径)**已于 R397 完成**(见 R397 节): 单一口径 **145/145 = 100.00%**, 且**口径敏感度实测 30.34pp** ⇒ ±5pp 不够用的根因是**口径自由度本身**。
取证件: `docs/reports/dcr/dcr-align-fava-source-2026-09-13.md`。

---

## R395 — BGE 闸门真修 + 停 cron + 融合线实测(RRF 可达值 0.8500)

**用户令 (逐字)**: "修完闸门 停 cron 走融合线"; 前置问 **"先告诉我一个结论, bge底座是否还需要自己二次训练, 有意义么, 提升性能代价多大?"**

**结论**: **不需要**。融合线(0 训练 / 0 新模型)真值: r@1 **0.5333** / r@10 **0.8500** / mrr@10 **0.6439**, 比最优单路(词法 0.7500) **+9.83pt**(网格最优; RRF 默认 k0=60 读数为 **0.8000**, +5pt), 比训练线最优(v11 r@10 0.6667) **+18.3pt**。

**因果链**: 训练线 9 轮 0 采纳的真因不是"数据还不够", 而是**收益天花板被零成本基线压住** —— 加数据到 1112 对后 r@10 只到 0.6667, 仍低于词法 bigram(0.7500)与 bge-base 底座(0.7417); 而互补性实测显示**词法 × dense-base 的并集口径已达 0.8667** ⇒ 真正有增量的是**融合**, 不是**训练**。

**两个真缺陷修复 (用户点名"修完闸门")**
| 缺陷 | 原状 | 现装 |
|---|---|---|
| G3 **口径分叉** | 文档 §5「延迟≤15% ∧ RSS≤15%」vs 代码「算力占比<5%」, 且代码从未测过真实耗时 | 三子判据同阈值实装: **算力≤5% ∧ 延迟≤15% ∧ 内存≤15%**; 延迟分母 = **绕缓存实测真前向**; 内存为**静态代理**(口径明写, 不得称 RSS 实测) |
| G5 **空心闸门** | 代码即 `g["G5"] = True` —— 确定性从未被检查, 却每轮记"G5 通过" | 真跑 4 条逐位判据: ①encode 重复性 ②顺序无关 ③秩可复现(与择优记录秩逐位比较) ④扰动负控 |

**真机证据**
- 闸门 A/B (同 1112 对 / 同算法 / 仅判定代码变): v11 `G1✓ G2✓ G3✓ G4✗ G5✓` ⇒ rolled_back; 指标 **与 v10 逐位相同**(0.3167/0.6667/0.4183) ⇒ **改判定不改结论, 只让结论变真**; G3 明细 `fwd_ms_per_vec 96.304 / lat_ratio 0.0109 / mem_ratio 0.00566`。
- 融合判据全绿: ①自建排秩与 `L.lexical_baseline` **逐位一致** + dense 两路与冻结节账(small 0.6333/base 0.7417)一致; ②单调变换后融合**逐位不变**, 负控改 120/120 条排秩; ③秩单调 fuzz 300 例; ④随机路 0.375 / 洗牌 0.0083(≈随机水平 0.0077)。
- 机检新增: `eval/bge/test_gates.py`(文档↔代码同阈值防漂移 + G3 两侧样例)、`eval/bge/test_fusion.py`(手算 RRF oracle + 三种可判别负控 + 边界口径)。

**停 cron**: 作业 `bge-idle-train(静默)` 已 pause(`enabled:false`, 停于 2026-09-13 21:49:48, 末次 v10), **未删除**可 resume; 停前 v10/v11 恰为该线最佳读数 ⇒ 属"见顶转线"而非止损。

**诚实边界**: ① 评测集仅 120 条(1 条=0.83pt), 主张取保守值 +5pt/+9.83pt 并列; ② 0.8500 为 36 格网格在**同一评测集**选优 ⇒ 选择性偏差已披露, 推荐读数 0.8000(k0=60); ③ 融合**产品侧端口未实现**(仅脚本级实测); ④ G3 内存子判据是静态代理; ⑤ 训练线唯一翻盘前提 = 接真实检索标注(属领域微调, 本机不支持 T2/T3)。

**教训归档 (通用化, Id/Pattern 无语言专名)**: 10.6 `gate.literal-true-is-hollow` / 10.7 `instrument.resolution-boundary` / 10.8 `control.injection-must-alter-observable` / 10.9 `assertion.must-be-provable`(见 `docs/plans/v0.22.0-exp5-lesson-table.md` §10.6–10.9)。

**报告**: `docs/reports/r395/r395-bge-gate-fix-fusion-and-cron-stop.md`; 融合报告(脚本自写, 禁手抄) `docs/reports/bge/fusion-2026-09-13.md`。

---

## R394 — prompt 缓存命中率红线 95% → 97%(口径权威单点变更 + 结构性归因机检)

**用户令 (逐字)**: "token命中率红线报警改为97%"。

**因果链**: 红线是**首要 KPI 的判定权威**, 其成立依赖两点: ①**单点权威** —— 阈值只有一个来源 (`PromptCacheRedline.Threshold`), Python `scripts/kpi_cache_hit.py` 的 `REDLINE` 与之机检锁死, 其它文件里的字节级代理断言必须**从常量派生**; ②**阈值 ⟺ 结构必需项** —— 阈值提高必须同步改"加厚前缀"的定量依据 (97% ⇒ 前缀 ≥4224 token 最坏对齐稳健界 / ≥2176 对齐最优)。

**本轮真缺陷修复**: 两处机检 (`SessionInjectionPlannerTests` 等) 仍带 **R380 之前的陈旧 90% 标签** —— 属"字节级代理断言", 改常量它照旧绿 (判定空心) ⇒ 改为**从权威常量派生**。

**顺带更正陈年口径残留**: 文档原写"红线等价于每轮增量 ≤ 前缀/9" (90% 旧口径 `hit/(hit+miss)`, 增量进分母)。**R380 口径依 `min(本轮,上轮)` 后增量与判定无关**: 有效命中率 = 命中上限/上轮前缀 = `1 − (64+r)/P`; 只有 prompt **收缩**才换分母。

**真机证据** (`docs/reports/r385/r394-cache-redline-97.md`):
- 聚焦 19/19 Passed (`Threshold = 0.97`)；全量 **1060/1060 Passed (33 s)**。
- 新阈值下真遥测: 轮2 **0.9574** / 轮3 **0.9543** / 按会话 0.9311~0.9689 —— **全部越线** (旧口径下"看着达标")。
- **结构性归因机检: 6/6 实测命中 == 结构上限 `(⌊P/64⌋−1)×64` ∧ 缺口 == 单元对齐损耗 `64+P%64`** ⇒ 越线 100% 归因**前缀厚度不足**, 装配侧缺陷 **0 例**。

**诚实边界**: 97% 在现前缀 (≈0.98k–2.55k token) 下**结构性不可达**(P=2551 上限仅 0.9533, 已吃满); 达标需前缀 ≥4224 token ⇒ 与"降低 tokens"存在张力, 留作用户裁定 (报告 §5 给出 A/B/C 三选项)。

## R393 — 本地 BGE 接入 Vulkan GPU 执行端口(端口化 + 真机对账 + 驱动约束取证)

**用户令 (逐字)**: "agent 本地bge也需要加vulkan gpu运行端口"。

**因果链**: 本地 BGE 一次嵌入的热点是**每层 6 次矩阵乘**(q/k/v/attn_output/ffn_up/ffn_down ⇒ 24 次 [seq,in]×[in,out])。若把"GPU 版"写成第二个前向, 立刻产生**两份前向语义**(LayerNorm/注意力/GELU/池化任一侧改动都要双改双测) —— 这是教训表 §10.2(同构多表示的形状静默错)的同类风险。故落点是**端口 + 单一前向**: 端口契约 `IMatMulBackend`(`src/agent.embedcpu/MatMulBackend.cs`), CPU 实现 `CpuMatMulBackend`(SIMD), Vulkan 实现 `src/agent.rover/gpu/VulkanMatMulBackend.cs`, 新建形状特化内核 `Kernels.MatMulBias(inDim,outDim)`, 前向本身**一行没多写**(只把 6 个投影改走端口)。

**交付**:
1. **端口契约与实现**: `MatMulBackend.cs`(新, 端口 + CPU 实现, 声明"纯函数 + 长度恰为 seq*outDim + 舍入语义"); `BgeCpuEmbedder(model, IMatMulBackend?)` 构造注入(**缺省 CPU, 行为与旧版逐位一致**), 新属性 `MatMulBackendName` 供证据; 删除私有 `MatMulAdd`(原样搬进 `CpuMatMulBackend`)。
2. **Vulkan 端口**: `VulkanMatMulBackend`(端口名 `vulkan`, 形状特化内核缓存, 三个形状断言 weight/input/bias, 暴露 `Dispatches`/`LastDispatchMs`/`PoolStats`); `agent.rover` 单向引用 `agent.embedcpu`(无环)。产品程序集**不引入 Silk.NET**(沿用 `agent.csproj` 既有边界)。
3. **内核**: `Kernels.MatMulBias` 4 绑定 (0=W 1=X 2=B 3=Y), `inDim/outDim` = 编译期常量(形状特化 ⇒ 内核内不用 ArrayLength 反推维度), 越界守卫 `i ≥ ArrayLength(Y)`; `Spv` 新增 `OpULessThan=176`/`OpUDiv=134`/`OpLoopMerge=246`/`ScFunction=7` + `LoopMerge()`/`FnVar()`(函数首块钩子 `Build(..., firstBlock)`), 全部经 `SpvRegistryAudit` 对权威 grammar 机检(新增 `ScFunction` 别名绑定, 否则审计红 —— 本轮真红过一次)。
4. **真机入口**: `agent.rover embed [--backend cpu|vulkan] [--device I] [--repeat R] [--text T] [--compare] [--selftest]` —— 输出全机器可读行(`bgemodel/port/vkdevice/membase/emb/determinism/parity/portcheck/pool/mem/done`), 零 shell / 零 Console 直写。

**真机证据**(`docs/reports/r385/r393-bge-vulkan-port.md`, 原始日志 `/tmp/r393/`):
- **端口确实被使用(防空心)**: `portcheck{dispatch_calls=expected}` 在 72 / 216 / 864 三种规模下 `match=True`(期望 = 层 4 × 6 × 文本 3 × 重复 R)。
- **数值对账**: Vulkan vs CPU `max_abs_diff ≤ 2.538E-007`, `cos=1.000000000`, `verdict=PASS`; CPU 档 `max_abs_diff=0.000E+000`(逐位相同)。舍入语义已写清: 内核**顺序**累加 vs CPU `TensorPrimitives.Dot`(**SIMD 多累加器**) ⇒ 不逐位相同, 故判据 = `≤1e-3 ∧ cos≥0.99999`(把"逐位一致"当判据会假红)。
- **确定性**: `repeat=3` 三个 pass `identical=true`(逐位)。
- **负控**: `--device 99` ⇒ `vkerr{note=device_index_out_of_range}` + `done{ok=false reason=device_unavailable}` 退出码 1, **不产出任何嵌入**(不静默退回 CPU)。
- **AOT**: 引擎侧 `IL_warnings=6`(全部第三方 `Silk.NET.Core.Loader` IL3000/IL3002) 且**原生二进制真跑 Vulkan 端口** PASS(无 JIT); 产品侧 `agent.host` publish **EXIT=0 / IL 警告 0 / 原生 14.5 MB**。
- **全量回归 1060/1060 绿**(1051 + 新增 9); 全解决方案 build **0 Error**; 本轮触及文件**新增 warning = 0**(`BgeCpuEmbedder.cs` 的 CA2014 经 `git show HEAD:` 比对确认为既有)。

**本轮最贵发现: 循环头不能带条件分支(规范合法 ≠ 驱动接受)**
- 首版内核把 `OpBranchConditional(cond, 循环体, merge)` 放在循环头 ⇒ `vkCreateComputePipelines: VK_ERROR_UNKNOWN`, 而自写结构校验器判**合法**。
- 一次性探针 `/tmp/r393probe` 最小变体二分(不入产品): 纯逐元素 ✅ / 函数局部变量 ✅ / `OpUDiv` ✅ / **循环头带条件分支 ❌(守卫有无、内存访问有无、分支极性三种改法都红)** / **glslang 形状(循环头只 `OpLoopMerge`+无条件跳转, 条件判定独立块) ✅** ⇒ 唯一变量是控制流形状。
- 修复采用 glslang 形状, 并**机检固化**: `MatMulBias_含唯一归约循环且循环头无条件分支` + 判别力负控 `MatMulBias_驱动约束检查器有判别力`(改回条件分支必须报 1 处违规)。

**内存观测(结论: 归因驱动, 不记为我方泄漏)**
- 原实现每次派发新建且从不销毁 6 类管线资源(真句柄泄漏) ⇒ 改造①按 (内核名,绑定数) 缓存; 改造②设备缓冲按 64 KiB 档位池化; 改造③命令缓冲常驻 + `ResetCommandPool`。
- 三次改造后 **RSS 斜率均不变**(≈76 KB/派发, 72/432/864 次派发实测), 而池读数证明我方有界: `pool{classes=5 slots=7 leases=3456 reuses=3449}`(**864 次派发只用 7 个设备缓冲, 复用率 99.8%**)。
- ⇒ 剩余增长落在 **lavapipe(软件 Vulkan ICD)内部**, 真 GPU 必须重测; **不记为我方泄漏, 也不声称已解决**(三次改造各有真实收益: 消除句柄泄漏 + 消除每派发 SPIR-V 重编译, 后者实测 `ms_per_embed` 693→558)。

**诚实边界**:
1. 本机唯一 Vulkan 设备是**软件实现**(llvmpipe) ⇒ 端口在本机比 CPU 慢(≈588–693 ms vs ≈249–259 ms/嵌入); **不提出性能承诺**, 真 GPU 复测判据/命令见报告 §6。
2. **产品侧未接线**: `agent.host` 进程内选 `vulkan` 需把 Vulkan 共享源接进产品并引入 Silk.NET, 会带入 6 条第三方 IL 警告 ⇒ **须用户决策**(本轮不擅自破坏既有边界)。
3. 循环控制流约束来自本机唯一驱动实现; 换驱动须复跑 `--selftest`。
4. 长文本(seq→510)只做了内核级数值对账(探针 `512×2048`), 未做端到端对账。
5. 踩坑: 给 `agent.host` 追加命令行 `-p:PublishAot=true` 会全局传播并命中 `netstandard2.1` 的 `agent.io` ⇒ `NETSDK1207`; 正确做法是只用 csproj 内置 `PublishAot`。

## R392 — 模块重命名 click-rover → agent.rover(目录/项目名/内部文件夹/命名空间全部小写, 类名不动)

**用户令 (逐字)**: "click-rover 更名为agent.rover 并且内部文件夹 类文件的命名空间 也需要小写 （类本身不用）"。

**因果链**: 模块名 `click-rover` 带连字符 ⇒ (a) 命名空间 root 只能写 `clickrover`(与目录名不同形, 二者漂移), (b) 内部文件夹首字母大写(`Cli/Gguf/Gpu/Spirv/...`)与命名空间 `clickrover.cli` **大小写不一致**, 同一目录在路径与符号里两种写法 ⇒ 引用面靠人记忆同步, 一旦不同步就是"编译过得去、文档与路径对不上"的静默漂移。R392 把**目录名 = 项目名 = 程序集名 = 命名空间 root = 文件夹名** 收敛成**同一串小写标识** `agent.rover`, 使"名字只有一处真值"; 同时保留类名(在 `.sln`/文档/registry 中作为符号引用, 改名无收益却有回归风险)。

**交付(全部带真机/机检证据)**:
1. **重命名映射(34 文件 + 1 计划文档)**: `src/click-rover` → `src/agent.rover`; csproj `click-rover.csproj` → `agent.rover.csproj`; `AssemblyName`/`RootNamespace` = `agent.rover`; 内部文件夹 `Cli→cli` `Formal→formal` `Gguf→gguf` `Gpu→gpu` `Gpu/Spirv→gpu/spirv` `Infer→infer` `Quant→quant` `Runtime→runtime`; 命名空间 `clickrover.*` → `agent.rover.*`。全部走 `git mv` + 脚本化文本重写(**不留人手抄**)。
2. **消费侧引用面同步**: `src/agent/agent.csproj` 共享源 `../agent.rover/formal/*.cs` + `../agent.rover/gpu/spirv/*.cs`(Link 同步小写); `eval/dcr/harness/dcrval.csproj`; `SpvRegistryAuditTests`(机检路径 + 目录探测); `docs/verification-registry.json` 的 `evidence_path`(**机检校验路径存在性, 不更新即红**); `scripts/kpi_dcr.py` / `eval/dcr/*` / plans / reports。
3. **解决方案接入(补齐 `agent.rover` 长期缺口)**: `dotnet sln agent.sln add src/agent.rover/agent.rover.csproj` ⇒ 工程数 16→17, 全解决方案 build **0 Error**。
4. **契约标识同步**: 插件 id `clickrover.formal` → `agent.rover.formal`(消费侧与契约文本同源常量 `FormalPromptContract.PluginName`/`ClickRoverSegmentPlugin.PluginId`, 由机检保证一致)。
5. **残留检查 = 0**(除已发布 HTML 报告逐字未动, 保其 sha256)。

**真机基线(重命名后, 与重命名前逐项对照)**:
- 全量回归 **1051/1051 绿**(与 R391 基线**同数**, `/tmp/r392/full_test.log`, 31 s; 干净无并发)
- 解决方案 build **0 Error / 66 Warning**(66 = 既有 warning 存量, 非本轮新增)
- **数值不变**: tiny 前向 `topk{rank=1 id=46 logit=4.420093}` 与 R388b 记录值**逐位相同** ⇒ 重命名未触碰任何计算
- 内核 `check --selftest` **14/14**(tokens=0); 驻留 `residency --selftest`(真 7B Q4_K_M) **10/10**
- Vulkan 真机: `done{command=vulkan kernels=3 pass=3 fail=0 spirv_valid=3 neg=5/5}`; `meta` 正常
- **AOT 发布复验**(改 agent 链代码后可执行产物必重发布): R391 收尾与 R392 各跑一次 `dotnet publish src/agent.host -c Release -r linux-x64` ⇒ `EXIT=0`, **IL 警告 0**, 产出原生 `agenthost`(NativeAOT, 无 JIT)

**附带发现并修复: 仓库内两份 DCR eval 快照是 R387 旧物(重命名逼出的真 bug)**
- **触发**: 按"改名后必须用真产物复验数值不变"的纪律复跑装配层评测, 发现仓库内 `eval/dcr/assembly_out.jsonl` / `eval/dcr/kernel_out.jsonl` **不是 R388 权威快照**, 而是 **R387 时代旧物**(各含 32 条 `Unknown`) ⇒ 与 R387 记录的 **DCR 132/145 = 91.03% / 覆盖率 60.69%** 对应, 比 R388 修内核后的真实值低 **13 条**。
- **根因**: R388 的真装配复跑产物落在 `/tmp/r388/`, **仓库内那份从未同步** ⇒ 临时目录里的权威快照 ≠ 仓库里的权威快照(同类根因: R390 的"跑旧 DLL"假象)。
- **修复**: 由**仓库内产物**复跑并**直接覆盖仓库文件** —— 装配层 = **AOT 原生产物** `agenthost --formal-eval eval/dcr/dcr_cases.jsonl`; 内核层 = 重命名后 `agent.rover check <case>.assert --json` ×145; 随后 `scripts/kpi_dcr.py` 重生成 `eval/dcr/dcr_report.txt`。
- **零漂移证明(两条独立腿, 各 145/145、0 差异)**: 新装配快照 vs R388 真装配快照 `field_diffs=0`; 新内核快照 vs R388 内核快照 `field_diffs=0`(**含 `note` 与反例变量取值**) ⇒ 重命名未改任何判定; 顺带 `ms` 由 R388 的 ~32.7 ms/条降到 **~0.18 ms/条**(AOT 免 JIT, 旁证)。
- **刷新后权威结论**(R392 历史读数; **R397 起单一口径定稿**, 禁止再并列汇报): **DCR(弃权计合规) 145/145 = 100.00%** / **保守口径 101/145 = 69.66%**(= 可决断集上限) / 覆盖率 101/145 = 69.66%(Proceed 51 · Violation 50 · Abstained 19 · Malformed 25) / 六类一致率**全 100%** / **主动误判 0**; z3 独立审计重跑 `AUDIT_RESULT=SOUND`(**30/30 反例为真 · 33/33 Proved 确 unsat · 0 假**), 与题集自带 `expected_verdict` **145/145 一致**。
- **文档同步**: `eval/dcr/README.md` §4.1/§4.2、`docs/reports/r385/dcr-s3-s4-results.md`(§4 标为 R387 留痕 + 新增 §8)。
- **新纪律**: 凡涉及仓库内 eval 快照的轮次, **必须用仓库内相对路径复跑并覆盖仓库文件**, 禁止只在 `/tmp` 留证。

**诚实边界**:
- 类名按用户令**不动**(`ClickRoverSegmentPlugin` 等), 因此"符号层"仍含 `ClickRover` 词形 —— 这是用户明示的取舍, 非遗漏。
- 计时类微基准 `SessionPerformanceTests.GetRecentMessages_BeatsFullTableSort_AtScale` 在与 build **并发**时出现过一次假红(`new 191µs < old/3 109µs`, old 被并发拉快); **无并发单跑 4/4 绿、全量单跑 1051/1051 绿** ⇒ 判为 2 vCPU 争用下的噪声, 非重命名引入。
- 已发布 HTML 调研报告内 2 处 `click-rover` 字样**故意不改**(线上产物 hash 已交付, 改动即换版)。

---

## R391 — 形式化闭环挂上主链(计划节点级本地验证 + 静态前缀条件契约注入)

**用户令 (逐字)**: "继续下一轮, 并结合当前 agent 能力做一次能力精简归拢(不必要的能力与步骤可以合并降低复杂度) 并于形式化验证引擎高度规划最合理的 agent 执行链" + "新 agent 链的计划要达到外部最强工程化实现给出的决策合规率为 90.5% 的 ±5 个百分点左右" + "进行下一步直到目前所有计划的任务全部完成"。

**因果链**: R386–R390 把形式化内核/闸门/GPU/驻留都做成了**独立可证伪件**, 但 agent 侧只到"闸门能拦节点" —— 模型**不知道**要产出形式化符号(C8 缺), 也没有一个"节点自带断言 ⇒ 本地裁决"的执行路径(C7 缺)。两者缺一, 内核就永远只是旁挂的评测件, 进不了主链 ⇒ 本轮把两侧接起来, 并让**注入侧与消费侧共用同一套围栏语义**(单一事实源 `ClickProofFence`), 否则会出现"注入了却读不到"的静默断链。

**交付(全部带真机/机检证据)**:
1. **C8 · 静态前缀条件注入**: `FormalPromptContract.Build()`(契约段: clickproof 围栏语法 + `no_formal: <理由>` 逃生口 + 逐条禁令) +
   `SessionBaseline.Build(root, formalPluginPresent)` **双槽缓存**(槽0=不在场 ⇒ 与 R380 前缀**逐字一致**, 零 token 负担; 槽1=在场 ⇒ 追加契约段)。
   **为什么必须双槽**: 单槽缓存会把两种前缀串味(先到的赢) ⇒ 前缀随调用顺序漂移 = 可复现性与缓存命中率**一起崩**。
   真机(生产组合根): 前缀 2800→3391 字符(+591, 估算 +358 token, 常量进静态前缀后每轮命中), 不在场前缀不含 clickproof。
2. **C7 · 计划节点级本地验证**: 节点正文自带机器可读断言 ⇒ `PlanRoutePolicy` 判 `Local` + `formal.verify` 执行器(`CarriesFormalClaim` ⇒ `ClickProofFence.ExtractTrimmed` 命中);
   执行器四态不可混算 —— `Proved`⇒放行 / `Refuted`⇒阻断且反例回注 / `Vacuous`⇒拒绝 / `Unknown`⇒**Failed 且 disposition=Abstained**(诚实弃权: 不计违规, 一样不放行);
   缺失(`NoFormal`)⇒放行且**绝不为此追问 LLM**(`RequiresLlmRetry` 恒 false)。
   真机(容器内**无任何 LLM 提供方**): `C_route location=Local exec=formal.verify`; n1 Proved⇒Completed, n2 Refuted⇒Failed, **total_llm_tokens=0** ⇒ 若误判远程必然硬失败。
3. **消费侧恒等透传铁律**: `ClickRoverSegmentPlugin` 处理含围栏段时返回内容与入参**逐字相等**(真机 `B_segment_identity=True`), 裁决只落账不改正文 ——
   段插件在回复链上, 改写正文会同时破坏缓存命中率与可复现性。
4. **同源封死静默断链**: 围栏标识与插件 Id 由注入/消费两侧**共用常量**, 机检 `Contract_Ids_Match_Consumer_Side` 钉死; 路由谓词亦与提取器同源(机检 + 负控: ```python 围栏/散文不得判本地)。
5. **一次真红并修**: 全量跑出 1 例红灯 `Unknown_Abstains_And_Still_Does_Not_Pass` —— 根因是执行器自造了第二套 Fall 文案, 与闸门不同源;
   改 `PlanNodeFormalGate.BlockMessage(d)` 后转绿。**该断言确实绑定了组件真实行为**(只查枚举名/恒真判定的空心断言不会红)。

**基线**: 三新套件 **26/26 绿**(契约 7 / 插件 8 / 执行器 11, 逐套件计数与 `--list-tests` 相符); **全量回归 1051/1051 绿**(上一基线 1025 ⇒ 净增 26, log `/tmp/r391/full_test.log`); 真机探针 11 条判据全绿(`/tmp/r391probe`, 生产组合根 `AddAgentFramework()` 装配, 原始输出 `/tmp/r391/evidence.log`)。

**诚实边界**: ① 本轮**不宣称** DCR 达标 —— FAVA 的 DCR 公式/分母/弃权处置仍不可得(T1–T4 开放), 仍须双口径敏感性分析;
② `Unknown⇒节点 Failed` 是**执行策略**(未证明不放行), 与 DCR 台账"Unknown 计合规(弃权)"是两个层级的口径, 不可混算;
③ 上游围栏回退(执行器支持)与路由判据(只看本节点正文)**不同宽** —— 已把"断言必须落在验证节点正文"写进 C8 契约第 5 条, 但**模型是否照做尚未在带 LLM 的真机会话里验证**;
④ token 增量为估算口径(中文 ~1 token/字), 非分词器实测。

---

## R386/R387 — 形式化闸门接线(调度器唯一前门) + 断言契约层 + 等待墙钟锚点 + DCR 评测入口

**用户令 (逐字)**: "进行下一步直到目前所有计划的任务全部完成"。

**交付(全部带真机/机检证据)**:
1. **M1 删空抽象层**: `ICapabilityPlugin`/`CapabilityPluginRegistry` = 零实现零注册(仅定义+一个 `FakePlugin` 测试) ⇒ 删两文件;
   **反证**: 删除后全量构建 0 错、全量测试绿 ⇒ 确认无消费方。M2 能力来源唯一: 保留 `CapabilityScanner` + `PanelData.CapabilityEntry`(全仓唯一定义)。
2. **断言契约层** `FormalAssertionContract`: 缺省(未声明)⇒`NoFormal` **放行且绝不为此追问 LLM**; 显式 `no_formal: <理由>` ⇒ 放行;
   `no_formal` 与 premise/goal 并存(自相矛盾)/残缺(缺 premise 或 goal)⇒`Malformed` 阻断。21 例单测含负向控制。
3. **节点级形式化闸门 — 第一次插错位置, 被真跑机检抓出**: 初版插在 `PlanRunner.RunNodeAsync`(产品路径的私有方法) ⇒
   端到端接线测试显示"被反驳契约的节点**执行体仍被调用**"(`order=["a"]`) ⇒ 说明该点**不是唯一前门**。
   迁到**调度器唯一前门** `TaskPlanExecutor.RunNodeCoreAsync`(任何被注入的 nodeRunner 都绕不过)后: 被反驳/片段外节点**零调用**且终态 `Failed`。
   **这就是"接线测试必须驱动真实调度器"的实证价值** —— 单测全绿但闸门在真链路上不生效, 只有端到端断言能暴露。
4. **内核语义修正(契约与实现不一致)**: 文档契约写"片段外一律 `Unknown`", 实测非线性前提(`x * x == 4`)被判 `Malformed` ⇒
   会把**正确弃权误记成畸形**, 直接扭曲 DCR 口径。修 `FormalKernel.FromParseFailure`: 片段外⇒`Unknown`(附 `fragment_limit:` 理由码), 真语法错仍 `Malformed`。
5. **`--formal-eval <cases.jsonl>`**(真实装配判定层入口, 零 LLM/零 daemon/零 shell): 8/8 冒烟覆盖 absent / declared / proved / refuted(附精确反例 `x=32818, y=-32808`) /
   vacuous / fragment(`Abstained`) / malformed / 自相矛盾; 每行 `would_call_llm=false`。**这是 DCR 可证伪测量的接口**。
6. **WaitUs 墙钟锚点**(R384 遗留⑤: 跨进程不可对账): `NodeWaitRecord` 增 `Started/EndedWallUtcMs` + `End()` **单一写点**(禁止两处各自取时钟) +
   3 条对账判据(`WallClockReconciled` / `WallClockOrdered`) + 负向控制(人为倒流必须判否)。时长唯一事实源仍是进程内单调时钟。
7. **R384 遗留④复核结论**: "答复落点与主链 `AnswerSink` 不一致" —— **`AnswerSink` 全仓 0 命中, 前提失效**; 真实落点是 `PlanResumeService.ApplyReply`(:206, 槽位名+范围校验, 不满足即拒绝)。
8. **登记**: `docs/verification-registry.json` 增 3 行(`formal.contract` L2 / `formal.node-gate` **L4** / `plan.wait.wallclock` L2), 机检 `VerificationFormTests` 6/6。

**基线**: 全量 **1019/1019 绿**; 闸门+接线 28/28; 契约 21/21; 墙钟+等待 35/35; 机检 6/6。

**诚实边界**: FAVA 原文正文(arXiv HTML/PDF/ar5iv/alphaXiv)本次均只取到摘要与引言 ⇒ **DCR 公式 / 分母 / 弃权处置 / aggregate 合并方式(T1–T4)仍未知**;
故 DCR 报告必须给**双口径敏感性分析**(弃权计合规 / 不计合规), 不得只报一个数。

---

## R380 — 缓存命中率口径修订(首要KPI) + 越线必查闸门 + 会话稳定基线 + 视觉能力目录纠偏

**用户 OOB (逐字)**: "将缓存命中率计算只计算需要命中的部分，当前轮新增不计入，因为肯定不触发缓存，并且记录到KPI首要任务内，一旦越过红线必然检查问题为什么发生并修复" / "将之前的红线提高为95%"

**口径修订**: 有效命中率 = `hit / min(本轮 prompt, 上一轮同会话 prompt)`
—— 旧口径 `hit/(hit+miss)` 把"本轮新增"(必然不命中)算进分母, 会把**已到结构极限**的轮次误读成灾难性失败
(真机 mt_fix4 轮2: 旧口径 66.08% vs 新口径 91.34%; 而该前缀的理论上限恰为 91.34%)。

**算术判决 (真机两样本一致)**: 命中 = `(floor(前缀/64) − 1) × 64` ⇒ 上限 ≈ `(n−1)/n` (n = 前缀 64-token 单元数)
⇒ 95% 需前缀 ≥2496 token (n≥39)、98% 需 ≥6336。**这是"红线提高必然要求前缀加厚"的定量依据** —— 结构修复到极限也只是把命中吃满上限。
实测校验: 前缀 981 → 上限 896 (观测 896)；前缀 2001 → 1920 (观测 1920)；前缀 2428 → 2304 (观测 2304)。

**修复**:
1. `PromptCacheKpi`: 口径 + `HitCeiling` + `PrefixTokensNeededFor`；**修未上报冒充 0 命中的真 bug**(机检抓到)。
2. `PromptCacheRedline`: 阈值 90%→**95%**；`Violated` + `Diagnose` (按四类破坏点给出可执行清单 + 算术判决)；router 越线即 `LogWarning` + `cache_redline_violation` 打点。
3. `SessionBaseline` (~3k 字符): 会话首轮焊进前缀 (纪律/命令/工作区快照/能力/模块地图/失败模式) —— 红线 95% 的算术必需项（**R394 已提高为 97%，本句为当时阈值**）, 之后每轮命中该段, 增量成本≈0。
4. `ModelQueueRouter` 逐轮归属打点 `cacheable_tokens`/`effective_hit_rate`；`scripts/kpi_cache_hit.py` 重写为首要 KPI (按轮次/会话聚合 + 红线判定 + 越线清单 + 退出码 -1 可做门禁)。
5. **模型目录纠偏 (真机实测推翻配置)**: `deepseek-flash` 原记 `image_input: false`, 实测其 API **支持图像输入** (读出测试图的"红色/SCORE 7/GAME OVER") → 改为 `true` (截图检验通路)。

**验收**: 机检 9/9 (PromptCacheRedlineTests: 口径/未上报/红线/上限公式/带内全扫/负向控制/真机回归)；真机 3 轮 (mt_fix5/6/7) 待汇总; 全量测试待跑。

**诚实边界**: 95% 在**短会话第 2 轮**仍可能因单元边界对齐而摇摆 (实测 95.95% / 94.90%) —— 加厚前缀后进入 ≥96% 区间; 与提供方实现相关的精确损耗模型仍需更多样本标定。

## R379 多轮会话缓存命中率根因修复 — 追加式前缀 + 增量最小化 (868/868)

**用户口令 (逐字)**: ①"关于目前命中率非常低的问题出现在哪里？一般不是90%多命中么？" ②"上下文 2000 token 预算 再自检的时候改成1M" ③OOB 红线: **多轮会话第 2 轮起命中率 ≥90%, 目标 98~99%**。

**根因 (请求体 dump + 最长公共前缀, 决定性实测; 官方规则: 缓存单元 64 token, 必须自 token 0 起完整匹配)**:

| # | 破坏点 | 位置 | 实测后果 |
|---|---|---|---|
| ① | `messages[0]` 逐轮改写 (forecastHeader 入 system + **意图漂移** search→general) | `IndustrialAgentV2.cs:1040-1049` / `:1035` | 第 2 轮 system 440→448 字符 → 公共前缀仅 **1.4%**, 自字节 93 断裂 |
| ② | 历史**滚动摘要重写** + `Take(10)` + **2000 token 预算砍头** | `IPromptBuilder.cs:197-215` | 第 3 轮命中率 **0.00%** (答案被压成 79 字符) |
| ③ | 回注块在 `SentContent` 快照**之后**追加 | `IndustrialAgentV2.cs:1232` | 发送字节 ≠ 回放字节 (实测差 72 字符) → 前缀中部断 |
| ④ | 每轮增量 ~850 token 而会话前缀仅 ~970 token | 装配点 | 命中率**算术天花板 ~53%** |

**修复 (追加式前缀 + 增量最小化)**:
1. **追加式回放**: 历史不重写/不砍头, `maxHistoryTokens` 2000 → **1,000,000** (用户令); 每轮重建的上下文块移到历史**之后**; `forecastHeader` 移出 `messages[0]`;
2. **`messages[0]` 会话内冻结** (`FrozenSystemPromptTable`): 意图漂移不再改写 system, 改为尾部一行短提示 `[本轮意图] general (会话人格保持不变)`;
3. **回注回写 `SentContent`**: 发送字节 = 回放字节 (单一事实源);
4. **增量最小化** (`SessionInjectionPlanner`): 会话静态块 (画像/偏好/工作区) 首轮焊进前缀、之后不再重复; 动态块**跨轮字节 + 近重复 (trigram Jaccard ≥0.75) 去重**; 用户本轮原始问题永不参与去重 (安全边界);
5. **KPI 逐轮归属**: `Prompt.SessionId`/`TurnIndex` → `llm_call` 打点 `agent_session`/`turn`; `scripts/kpi_cache_hit.py` 增按轮次/会话聚合 + **红线判定** (多轮第 2 轮起 ≥90%)。

**机检 (9/9, 含负向控制)**: `MultiTurnCachePrefixTests` 4 (逐字节追加式前缀 / 红线占比 / 负向控制: 变量放 system 必须破前缀 / 1M 预算不丢消息) + `SessionInjectionPlannerTests` 5 (静态块识别 / 跨轮去重 / **红线: 增量占比 ≤10%** / 标题行恒保留 / 近重复抑制)。

**真机 4 次复测 (单会话 3 轮, 每轮请求体落盘)**:

| 口径 | 轮 1 | 轮 2 | 轮 3 |
|---|---|---|---|
| R379 基线 (修前) | 30.26% | **62.28%** | **0.00 / 13.66 / 11.82%** |
| R379 修后 (mt_fix4) | 13.05% | **66.08%** | **72.44%** |

- 结构指标: `messages[0]` 会话内恒定 **1149 字符** (修前 440→448); 轮2→轮1 公共前缀 **99.4%**, 轮3→轮2 **99.6%** (逐字节追加); 每轮调用数 1 (修前第 3 轮 3 次调用), 前缀不砍消息。
- 增量构成 (轮 2, 526 字符): 问题 13 + 意图提示 26 + 下轮预估 32 + SessionMemory 84+24 + **Memory(RAG) 261** + 回注 12 + 联想 27+29。

**诚实边界 (未达红线)**:
- 轮 2/3 = 66.08% / 72.44%, **红线 90% 未达**。算术: 命中率 ≈ 已发前缀 token / 本轮总 token; 要 ≥90% 则**每轮增量 ≤ 前缀/9**。现前缀 981 token, 增量 ~375 token (RAG 140 + 记忆 60 + 联想 30 + 估/意图 30 + 回答 90 + 问题 7) → 上限 ~72%。
- 每轮"必须发"的只有回答 (~90) 与问题 (~7); 其余全是逐轮注入 → **要么停止逐轮注入新召回 (追问轮), 要么把会话稳定前缀做厚到 ~3000 token**, 二者皆是产品策略选择 (质量 vs 缓存 KPI), 待用户裁定 (本轮已把可无损失拿到的部分全部拿到: 静态块提升 + 近重复抑制)。

## R377 DS prompt 缓存命中率纳入优化 KPI（用户钦定）— 解析 + 三处打点 + 离线聚合 (859/859)

**状态**: 已实施并验证（L2 机检 12/12 + L3 真机样本 + L4 负向控制；AOT 参考 13,959,760 B / 0 IL，按 R7 不登记）

- **口径（用户 2026-09-13 钦定）**: 模型返回的 `usage.prompt_cache_hit_tokens` / `usage.prompt_cache_miss_tokens`
  → **命中率 = hit / (hit + miss)**，作为 **K2（token 使用量）成本侧子指标 K2b** 纳入优化 KPI。
- **实现链路**: `OpenAIChatUsage`(+2 可空字段) → `QueueResponse` / `LLMResponse`(+2 字段) → `ModelQueueAdapter` 透传；
  新增 `PromptCacheKpi`（4 位小数 + 未上报哨兵 `-1`）；**三处** data-carrying `llm_call` 打点（主路径 / 重试 / 兜底）都铺
  `cache_hit_tokens` / `cache_miss_tokens` / `cache_hit_rate`；离线聚合 **`scripts/kpi_cache_hit.py`**（按模型分组 + 未上报计数 + JSON 落 `eval/results/`）。
- **铁律（诚实边界形式化）**: **未上报 ≠ 0 命中** —— provider 未给字段时记 `-1` 且**不并入比率**；分母为 0 同样记 `-1`。
  真机实证该区分有效: 全量遥测 45 次调用中 **41 次未上报（历史无此字段）+ 4 次上报**，脚本如实分列，**不把 41 次读成 0%**。
- **真机样本（同题贪吃蛇连跑 2 次；`/tmp/gameprobe/run_r377.sh`）**:

  | 跑次 | 调用 | tokens | hit | miss | 命中率 | 产物 | D3 修复回流 |
  |---|---|---|---|---|---|---|---|
  | RUN1 | 2 | 37,226 | 1,280 | 4,114 | 23.73% | 2（首投 exit=1 → 修复 exit=0） | 触发 1 次 |
  | RUN2 | 2 | 39,955 | 2,048 | 3,496 | **36.94%** | 2（首投 FAIL 14/16 → 修复 ok 16/16） | 触发 1 次 |
  | 合计 | 4 | — | 3,328 | 7,610 | **30.43%** | — | 2/2 成功 |

  **独立复核**（自己跑闸门，不信遥测自报）: RUN1 `py_8606386f --selftest` → `exit=0 · ALL PASS (16/16)`；RUN2 `py_a7fa39a7` → `exit=0 · ok (16/16)` ✓。
  第二次命中率更高（23.73% → 36.94%）= 同一前缀被复用，KPI 方向符合预期。
- **机检**: `PromptCacheKpiTests` 12/12（DTO 解析 / 未上报为 null / 命中率边界含真·0 命中 / 三元组固定 / **按打点块配对**的接线扫描）。
- **负向控制 3 组**: ① 命中率分母 +1 → **4 红**；② `HitTokens(hit) => hit ?? 0`（未上报冒充 0）→ **1 红**；③ 删一处打点铺设 → **1 红**。
  **首跑变异③ 曾 0 红** —— 我的扫描断言当时只数「助手出现次数」（空心判定）→ 改为**按打点块配对**（每块必须真含 `cacheKv[0], cacheKv[1], cacheKv[2]);`）后抓到。
- **诚实边界**: ① 命中率为 2 跑样本（同题），非稳态生产分布；② 本轮样本 tokens（37.2k / 40.0k）高于 R376 的 19.2k，
  原因是**两次首投产物自测均失败 → D3 修复回流各多 1 次调用**（机制正常工作，成本如实登记，不做"优化了"表述）；
  ③ 首跑全量 857/859（2 红未留名）→ 随后连续两跑 **859/859**，判负载偶发（同 R374/R375 类）；**下轮候选**: socket 测试族串行化以消抖。

**基线**: 全量 **859/859**（R376: 847/847）；命中率 KPI 首发样本 30.43%（4 次调用）。

---

## R376 exp2 P2 达成 — 真机同连接 menu 闭环 + 两处断链修复 (⑪ 握手残包 / ⑫ 回程饿死) (847/847)

**状态**: 已实施并验证（L2 机检 + L3 真机闭环 + L4 负向控制；AOT 按规范 R7 本轮不登记）

- **靶点**: R375 遗留的 P2「真机 `chat.send` 收不到结构化 ask 事件」。
- **根因（遥测实证，非推测）**: R375 同题遥测 `evidence_gate{subtasks:1,suspects:0,to_ask:0,confidences:"1"}` —— 清晰题置信度 1.0 ≥ 0.60 阈值，**证据门根本没触发**（不是通道坏）。
  触发配方由代码给出（`IntentDecomposer` 启发式，0 token）: 指代不明 −0.25 + 通用意图弱信号 −0.20 → **0.55 < 0.60**。
- **真机闭环（P2 达成）**: 新探针 `/tmp/fp376/probe2.py`（AOT 二进制 + 真 TCP + 真 token）连跑 3 次全部走通:
  `ask 事件`（`ask-*`，`timeout_s=300`，`questions[1]`）→ **同一连接** `ask.reply` → `resp{outcome:answered}` → `ask_closed{answered}` → **续跑返回真实正文**。
  遥测: `evidence_gate{subtasks:1,suspects:1,to_ask:1,confidences:"0.55"}` + `loop_turn{total_ms:4054,success:true,reply_chars:119,asked:true}` → `gate_to_ask=True`（R375 为 False）。
- **顺带修两处真缺陷（真机暴露，均带负向控制）**:
  - **⑪ 帧边界 / 握手残包**: `FrontendApiServer.TryAuthHandshakeAsync` 单次整块读取后**丢弃换行之后的字节** → 客户端把 auth 与首个请求合并发送时首请求静默消失（R375 探针靠 `sleep 0.8` 绕行）。
    修复: 握手返回残包 `Tail`，请求循环**预置缓冲并先排空**，不丢字节。
  - **⑫ 同通道回程饿死（更严重）**: 读循环 `await` 请求执行 → 请求处理内部触发 ask 并等答复，而答复在**同一条连接**上永不被读 → 双向死锁至 300s 超时。
    **单测全绿的原因** = 触发源被**带外构造**（直接调 `RequestCredentialsAsync`），读循环空闲 → test-blind-spot。
    修复: 读循环只做**解析 + 并发派发**（`Dispatch`: 在途上限 8、异常必观测、发送面共用连接锁保证行不交错），断开前给在途请求 2s 有界收尾。
- **契约澄清（已入 registry）**: ① 并发派发下响应**按 `req_id` 关联**，不保证到达顺序；② 同通道上**事件与响应相对顺序不保证**（测试断言改为顺序无关且暂存不丢）。
- **机检**: 新增 `FrontendHandshakeTests`(4) + `FrontendAskSameConnTests`(2)；过滤族 **23/23**；全量 **847/847**（R375: 841/841）。
  **负向控制 2 组**: 丢弃握手残包 → **2 红**（两种变异各 2 红）；读循环改回等待长任务 → **2 红**（均已还原，字节一致）。
- **能力探针（R376 回归样本，同题贪吃蛇，CLI 主链）**: 1 次调用 / 76.7s / **19,191 tokens** / 产物 14,368 B `origin=fenced` / `script_run exit=0`；
  **独立复核** `python3 -I <产物> --selftest` → **exit=0 · PASS (34/34 项)**（不信任遥测自报）。
- **通用教训沉淀**: `skills/delivery-selfcheck/SKILL.md` → v1.1.0 新增「步骤 6 · 通道核查」（帧边界 + 回程饿死 + 有界并发 + 顺序无关）；
  「正文核心零语言特性」机检 **19/19** 通过（含负向控制：注入语言 token 必红）。
- **诚实边界**: ① 真机样本 n=3（同题三次均闭环）；② tokens 19,191 vs R375 17,188（**+11.7%**，产物自测项 34 vs 13，单样本、模型侧生成差异，非机制开销）；
  ③ 在途请求**不随客户端断连取消**（2s 收尾后放弃，与修复前同语义，登记为已知边界）；④ exp2 §8 Q1–Q4 仍**待用户裁决**（本轮沿用 R375 推荐口径）。

**基线**: 全量 **847/847**；AOT 参考 13,959,712 B / 0 IL 警告（按 R7 仅作参考，不登记）；提交见本轮 commit。

---

## R375 exp2 P0 前端 menu 问询通路实装 — 信封 + 事件推送 + ask.reply/ask.cancel + 选项贯通 (841/841)

**状态**: 已实施（L2 机检 + L3 真机接线证明；生产侧命中率 0/1 如实登记；AOT 按规范 R7 本轮不登记）

- **缺口（exp2 P0 三处）**: ① `FrontendPromptService` 的 `emitEvent` **无提供者** → 前端模式下问询事件直接消失（A 栈 `Options` 有字段、零消费方）；
  ② 事件**不成信封**（裸 `{ev:"ask",...}`，与契约 `{v,type,event,payload}` 不一致）；③ 选项/数据类型**只拼进 Display 文本**，前端无法渲染菜单。
- **实装**:
  - **契约面**: 新增 `src/agent.frontendapi/AskEnvelope.cs` — 手写 `Utf8JsonWriter`（零反射/AOT）产出 `{"v":1,"type":"event","event":"ask","payload":{ask_id,service,purpose,timeout_s,group_size,questions[]}}`，单题含 `data_type/multi_select/default_value/options[{value,label,recommended}]`；另有 `ask_closed{reason: answered|timeout|cancelled|superseded}` 与 `TryParseReply`（空 id / 非对象 / 非 JSON → 显式拒）。
  - **通道面**: 新增 `FrontendEventHub.cs`（进程内唯一出站口）+ `FrontendApiServer.EmitEventAsync`（已鉴权在线连接广播）+ **单连接发送锁**（事件与响应不再可能交织成半行）；`FrontendApiChatRouter` 新增 `ask.reply` / `ask.cancel` 路由；`FrontendPromptService` 支持超时 / 取消 / 被取代 / 幂等（`already_answered`）。
  - **模型面**: `CredentialItem` += `DataType/Choices/MultiSelect/DefaultValue`（+ `CredentialChoice`）；`ClarificationBatch` 结构化下发选项（不再只拼文本），回答仍走原 `PromptDataValidator` 选项校验 → 菜单选择是**真闭环**而非显示优化。
  - **主机接线**: `Program.cs` 在 `--frontend-api` 模式下**覆盖** DI 的 Console 实现（DI 单服务解析取最后注册者）→ `IndustrialAgentV2` 经 DI 拿到前端问询实现；服务器上电前挂接出站面。
- **机检**: 新增 `AskEnvelopeTests` **8/8** + `FrontendAskFlowTests` **6/6**（真 TCP + 真信封：事件抵达含 options / 回复后调用方拿到答案 / 未知 id 不误投 / 取消返回 null / 超时 1s / 幂等 already_answered）；原 `FrontendApiTests` 4/4 不回归。
- **负向控制（真红实测）**: ① 回退裸 `{ev:"ask"}` → 5 红；② `BuildQuestions` 丢 options → 1 红；③ `Complete` 去掉 ask_id 校验 → 1 红（防误投）。
- **真机（L3/L4，`/tmp/fp375/probe.py`）**:
  - **P1 确定性（真 `agenthost` 二进制 + 真 TCP + 真 auth token）**: `meta.ping ok` / 伪造 `ask.reply`、`ask.cancel` → `payload.outcome=unknown_ask`（**未接线时会是 `channel_unavailable`** → 据此证明真机 DI 已换实现且通道已挂接）/ 空 envelope → `error.code=bad_payload` / `state.snapshot ok`。
  - **P2 真实 `chat.send`（deepseek-flash，1 次）**: **ask 事件 = 0/1** → 模型走**散文澄清**（reply 前缀 `[隔离任务]`），未触发结构化问询。生产者存在（`IndustrialAgentV2.cs:1878` EvidenceGate 裁定；`NodeExecutionResult.cs:332` node.Clarifications）但本次判据未命中 → **只登记「机制已通」，不登记「管线会问询」**。
- **真机顺带发现（⑪类新断链）**: 前端**握手整块消费首帧** → 与 auth 同一 TCP 段到达的首个请求被静默吞掉（探针首跑无响应、客户端表现为挂起；加 0.8s 间隔即通）→ 下轮候选修复（残包交还主循环）。
- **能力探针回归样本（同题贪吃蛇，`/tmp/gameprobe/run_r375.sh`）**: 真机 **1 次调用 / 82s / 17,188 tokens**（prompt 2,359 + completion 14,829；`first_budget=32768` 生效、`truncated=false`、`empty_reply=false`、`content_len=16092`）/ 产物 `py_936eb4414f523505.py` **16,842 B** `origin=fenced` `compile_valid=true` `exit=0`；**独立复核**（不信任遥测自报：`python3 -I <产物> --selftest`）**exit=0 · 13/13 用例通过 · PASS** → R375 改动（仅前端模式路径）**未回归 CLI 主链**；同题 tokens: R373 基线 18,029 → **17,188（−4.7%）**。
- **基线**: 单元测试 **841/841**（R374: 827 + 信封 8 + 真 socket 6）；AOT 见下方参考证据（按 R7 非发布 tag 不登记）。

## R374 运行结果回流闭环 D3(自我迭代) — 失败输出回流 + 有界修复 + 复检 (827/827, AOT 0 IL 警, 13,842,384 B)

- **断链 D3(运行结果回流)**: 产物校验失败时, 运行输出(stdout/stderr/未通过用例)在插件内部被丢弃 — 台账/遥测只留一个 exit 码
  → 失败信息**从未回到模型上下文**, 「自测失败」与「任务结束」没有区别, agent 无法自我迭代。
- **数据面**: `ArtifactCheck`(失败类别/退出码/输出尾部/自测入口判据) 经 `IArtifactCheckSource` 上抛,
  路由器 `DrainArtifactChecks()` 聚合(含通过项 — 复检需要「通过」证据); 产物报告新增 `OutputExcerpt`(失败输出不再丢)。
- **闭环面**: `ArtifactRepairLoop`(主链交付段后接线) — 校验失败 → 失败输出 + 失败脚本 + **闸门契约** 回灌模型
  (`Intent=code_generation`, 复用 R373 首轮预算) → 修复轮产物重新过闸 → **复检铁律: 必须出现「新路径且通过」的产物**
  (同路径 = 内容未变 = 没修好)。有界 1 轮; 闸门 `AGENTFRAMEWORK_ARTIFACT_REPAIR`(默认开)。
- **机检**: `ArtifactRepairTests` **10/10**(含闸门契约/未通过用例摘要/最小改动约束的可见性断言; 摘要只摘原文行且上限 12);
  负向控制双向实证: ① `IsRepairable` 置 false → **4 红**; ② 复检放宽为「任意通过产物」 → 非确定性用例 **1 红**。
- **真机 A/B(同题 3 连跑, 同一二进制, 仅环境变量开合)**:

  | 臂 | 每题调用 | tokens 合计 | 最终交付有效 | 触发回流 | 修复成功 |
  |---|---|---|---|---|---|
  | A 回流关 | 1/1/1 | 50,885 | 2/3 | 0 | — |
  | B 回流开(旧提示词) | 2/2/1 | 88,435 | 2/3 | 2/3 | 1/2 |
  | D 回流开(新提示词) | 2/1/1 | 77,270 | **3/3** | 1/3 | **1/1** |

  铁证: D RUN1 `artifact_feedback{fixed:true, error_kind:run, ms:70465, tokens:23306, detail:复检通过 py_659e45659066faf1.py}`,
  且制品链 `py_b6ce831c168371b0 (run_exit=1) → py_659e45659066faf1 (run_exit=0)` 全在遥测里可核。
- **提示词改进(真机驱动, R374b)**: 修复轮必须写明**闸门契约**(`python3 -I <文件> [--selftest]`、无 stdin/TTY、要求退出码 0)
  + **未通过用例原文摘要** + **最小改动/不得回退** — 与 R371 D4 同类教训(组件入口约定不写进上游纪律 → 无从满足)。
- **诚实边界**: ① n=3/臂, 跨臂「最终有效 2/3 vs 3/3」是抽样, **不能当统计结论** — 可断言的是**机制**(触发/回流/复检/归因)
  与**失败才付费**(首投成功路径 1 调用 ~15.6-16.7k tokens, 与 A 臂同量级); ② 失败路径成本 +1 调用 +23.3k tokens +70s;
  ③ A 臂「交付了自测失败的产物」用户无感知(只在遥测), D 臂同类失败至少被如实标记(可观测性提升, 不等于修好了);
  ④ 修复成功率仍受模型能力限制(旧提示词样本 1/2)。
- **环境卫生教训(本轮实证)**: 探针脚本曾把 `AGENTFRAMEWORK_PY_RUN=1` **全局 export** 进 `dotnet test` 进程 →
  env 敏感用例(`PythonRunVerifierTests.闸门取值_只认显式开`)必红。已改为只对真机执行段注入; `env -u` 复跑 **827/827**。

## R373 首轮预算策略(接线缺口修复) + 经验沉淀为思考逻辑 skill (817/817, AOT 0 IL 警, 13,817,472 B)
- **断链 D8(接线缺口)**: 路由器的首轮预算策略实现正确、12/12 单测全绿, 但**调用方把任务分类硬编码成 "general"** → 策略永不触发(死代码)。
  修复 = `Prompt.Intent` 从真实上下文透传(意图识别 → 适配器 → 路由器) + **接线级测试**(经真实适配器驱动) + RED 控制。
- **真机 A/B(同题 3 连跑)**: 每题调用 **2→1** · 恢复触发 **3/3 轮→0** · tokens/题 **−32%**(18029→12289) · 墙钟 136s→64s · 有效产物 **1/3→3/3**;
  遥测归因 `first_budget=32768 / intent=code_generation`。**根因假说成立**: 推理与正文共享输出预算(修复后单轮 `reasoning_len=56033` 仍不截断)。
- **经验落库形态(R373 用户钦定)**: 可复用经验沉淀为**思考逻辑 skill**(`skills/delivery-selfcheck/SKILL.md`: 判据先行→完整性→预算→接线→归因),
  **核心判据零语言特性**(机检 + 负向控制); 真机 `skill_match top1` 命中(此前同一题错配 image-gen)。
- **新缺陷 D9-a(真机当场暴露并修复)**: 初版 `type: normative` → `skill_trigger=force` 把技能正文当答复直出(无 LLM 调用/任务被劫持);
  改 `knowledge_hint` 后命中仅注入知识, 回复仍走主链 → 产物 19172B 有效。机检已锁死形态。

## R371 能力差异探针(py 游戏) → 七处断链修复 + 无围栏代码入链(含归因) + 教训表/运行级验证收口 (802/802, AOT 0 IL 警)

- **用户指令 (逐字, 三条)**:
  1. "请将bge设置为静默后台长期任务，只用汇报给我之前的5个需求和 【通过查看自己的上下文来对比当前项目agent能力（通过py开发一个游戏）差异】 这项任务，你可以先内置py插件"
  2. "真跑 agent 产出的 artifact 自测 时记得将可复用的模块做成skill放在skills内，并且可以允许对已有skill进行优化、删除、更名等操作（注意所有代码类型的必须为通用形式），一切以KPI（tokens\用户回答频率不能高\回复质量，同一个问题优化前后需要多少tokens和多少轮）和通过上下文自检为要目的"
- **探针方法**: 同一提示词（Python 贪吃蛇 + `--selftest` 无头自测）→ ① 宿主侧一条链做完（**PASS**）；② 项目 agent 用 **AOT 真产物**跑 → 逐环节对比。
- **五处断链点（全部真机实证 + 修复 + 机检）**:
  1. **D1 空正文被判成功**（最严重）：`llm_call completion=8192(=上限)/content_len=0/reasoning_len=22633` 且 `loop_turn reply_chars=0 success=true`
     → 推理模型吃满输出预算，框架只对 HTTP 异常重试、**从不检查正文是否为空**。修 `ModelQueueRouter`：检测 → 升级预算(8192→32768)+抑制推理提示重试一次 → 仍空则**可见降级 + Success=false**；遥测不再无条件 `success=true`。
     **修复后真机铁证**：`llm_call_recover: first_content_len=0 → retry_content_len=11345, recovered=true`（同一天同一提示词，缺陷真实复现并被自动救回）。机检 `EmptyContentRecoveryTests` 3/3。
  2. **D4 裸代码 → 机器链全程不触发**：回复 9232 字符完整实现、却**零 `script_artifact` 遥测**、`data/artifacts/` 无新文件。
     排查先自证伪（围栏正则被怀疑转义写坏 → 用独立 Python 复算 C# 字面量 → **正则正确**）；真因=**输出纪律从未要求代码围栏**，
     而插件只认 ```python → 契约不匹配；且第 7 条"500 字以内"与"交付完整单文件"直接冲突。修：输出纪律第 9 条（代码必须围栏 + 解除字数限制）。
     修复后：`script_artifact py_4ec069d5.py 12156B compile_valid=true`，**复跑其 `--selftest` → PASS (18/18)**。
  3. **D2 发布产物不自带 config**：AOT 产物在仓库外 cwd 运行 → `模型目录为空`。修 `agent.host.csproj` 让 publish 携带 `config/{base,modules,env}`
     （凭据只存环境变量名）；验证 `CONFIG_SHIPPED=/tmp/pub_aot_r374/config/base`。
  4. **D5 运行级验证选参 + 结论上屏**：交互式产物被无参运行必然卡到超时；CLI 只显示编译结论。修：产物含 `--selftest` 时自动带参（保守），
     CLI 追加 `· run exit=<code> (<ms>)`（未开启不显示，不假装验证过）。
  5. **D6 相对路径 → 运行级验证假阴性**：插件传相对路径而子进程 cwd 被切到脚本目录 → `python exit=2 (50ms)` 秒退，与"真跑 PASS 18/18"矛盾。
     修：`Path.GetFullPath(scriptPath)`；**RED→GREEN 负向控制**（撤销修复 → `Expected 0 / Actual 2`；恢复 → 12/12）。
     **v2（真机 RUN3 驱动, R372）**: v1 上线后 3 连跑命中 **2/3**, 未命中那次正文带**中文 docstring** → v1 的 35% 散文闸门把**字符串字面量内部**的行当散文而误拒。
     修: 三引号状态机(串内行记中性 + 强制 `code=false`); 新增 `ResponseSegment.Promoted` 归因 + `script_artifact.origin`(fenced / heuristic) → 产物**来路可归因**。
     机检 **9/9**(v2 新增 3 例: 文档健全实现必须提升 / 归因字段 / 截断半份仍可提升)。
  7. **D7 截断正文被判成功**(RUN3 真机铁证: `completion_tokens=8192(上限) content_len=1209 success=true`, 正文停在 `start_len: int =` **半行**) —— D1 的姊妹病(D1=空正文, D7=半正文):
     修: `LooksTruncated` **纯语法判据**(尾部为 `= ( [ { , : + - * /` 或反斜杠 / 引号或围栏未闭合; 全角句号结尾不误报) → **升预算 + 断点提示的有界续写一次** →
     `MergeContinuation` 去重重拼(重叠 >=6 字符且含非空白才算证据, 纯空白重叠不删以免吃掉缩进); 续写为空则保留原文并如实标记; 始终落 `llm_reply_truncated` / `llm_call_continue` 遥测。
     机检 `TruncatedReplyRecoveryTests` **15/15**(真 HTTP 假端点; 完整正文 1 次命中零额外成本 / 续写空不假装完整)。
  6. **D4-b 无围栏代码 → 产物链仍不触发**（D4 的**提示词级**修复不确定：3 次真机仅 1 次带围栏）：
     改在**分段器**里做保守启发式提升（**零额外 token / 零额外轮数**）：`ResponseSegmenter` 在无围栏时定位"整段代码" ——
     取**首个代码行**起、至**最后一个代码行 + 紧接其后的空行/注释**止；段内散文占比 > 35% 即放弃（**宁可漏提升，不可误判**：误判会把散文当代码落盘/编译 = 假证据）；
     命中后渲染层自动补围栏 → 用户看到的输出同时被**规范化**。
     机检 `UnfencedCodeDetectionTests` **6/6**（含无围栏文本经路由器 → **真 `py_compile`** 落盘；3 项负向控制：纯散文不误判 / <8 行不提升 / 已带围栏不重复）；
     **RED 控制**：关闭回退 → 3 个用例如期变红。
     **算法教训（语言无关）**：*启发式边界的终止条件必须锚定"最后一个确证项"；弱证据（空行/注释）只能附着于确证项，不得凭相邻性把无关内容并入* —— 首版把"尾部空行"当延长依据，导致其后散文被吞进代码段（机检当场抓到）。
- **L5 运行级验证 (t8–t12)** 收口：默认关、零 shell、超时杀树、输出上限排空、结构化结果、插件接线；族内 20/20（含 300k 排空 / 路径含空格引号 / 闸门关不执行 / 相对路径回归）。
- **exp5 教训表（role 模块）核心**：`LessonGeneralization`（通用化机检）/`LessonTable`（FNV-1a 指纹 + 去重归并 + 版本游标 + STJ 源生成 + 原子写）/`RoleLessons`（无 role 不落盘且显式回报）；11/11 机检（A8 负断言：`py_compile`/`C#`/`.cs` 一律拒收）。
- **exp8 立项**（用户本轮新钦定）：[已验证产物 → skill 蒸馏 + skill 生命周期 + KPI A/B](./plans/v0.22.0-exp8-artifact-to-skill-and-kpi-ab.md)（设计文档，含 tokens/轮数/asked 率/质量 对照口径与 A1–A6 机检草案）。
- **静默后台**：bge 闲时训练 cron 改为 `deliver=local`（只落盘不打扰）；探针全记录 `docs/plans/v0.22.0-r371-capability-probe-python-game.md`。
- **真机 A/B（R372, 3 连跑）**: 产物命中 **1/3 → 2/3 → 3/3**；**有效产物 2/3**（RUN2 截断致 `compile_valid=false`）。
  **归因反转（诚实点）**: 3/3 全为 `origin=fenced` → 本轮命中率提升来自模型给围栏（D4 提示词纪律），**非** D4-b 启发式；若无 `origin` 字段会把功劳误记给启发式。
  **D7 真机首触发**: `completion=8192 / content_len=7510 / truncated=true / reasoning_len=20159` → 续写 `before=2735→after=7510 / still_truncated=true / recovered=false`（未救回，如实入库）。
  **根因假说**（下轮验证）: 推理与正文**共享输出预算**（D1 空正文 `reasoning=22633/content=0` 与 D7 同源）→ 正解是首轮按任务给足预算，续写仅兜底（省 tokens/轮数）。
- **基线**: 单元测试 **817/817**（R372: 802 = 778 + D4-b 9 + D7 15; R373: +首轮预算 12 + 技能通用化 3）/ AOT linux-x64 **0 IL 警告**, `agenthost` **13,817,472 B**, 发布自包含（自带 config）。
- **诚实边界**: ① 探针只覆盖"生成代码"单场景，未覆盖多轮迭代式修复；② 运行级验证默认仍关（需 `AGENTFRAMEWORK_PY_RUN=1`）；
  ③ D3（运行结果回流给模型以自我迭代）**未做**，登记待办；④ exp8 仅设计未实现；
  ⑤ D7 续写的**真机复现**尚未取到（RUN3 那次截断发生在修复前）；`llm.truncated.continue` 的 L3 证据列为下轮必取项；⑥ 引擎侧无"按预算主动分段"策略，截断仍靠事后补救。

---

## R370 验证形式入规范 + 跨会话检索 + 运行级验证 + 教训表(role) + bge 召回实测反转 (772/772, AOT 0 IL 警)

- **用户指令 (逐字, 两条)**:
  1. "继续下轮，注意别忘验证形式，要加入规范内，【通过查看自己的上下文来对比当前项目agent能力差异】并修复完善"
  2. "收集未来可用于bge-small-zh-v1.5基座的数据，并加入闲时训练计划，本机若无任务再执行就自动执行数据收集，训练bge版本，统计KPI不断择优，请你以确定性的召回率为目标不断优化bge-small-zh-v1.5 并生成每个版本小报"
  3. (后续) "注意别忘验证形式…和 之前的5个开发计划的实施" + "你需要实测它们用于召回的能力后再最终确定用哪个嵌入模型"
- **L1 验证形式入规范 (用户长期焦点, 本轮交付)**: 新增 [docs/验证形式规范.md](./验证形式规范.md) (证据阶梯 L0 未验证 → L1 静态 → L2 单测/组件行为 → L3 真机运行 → L4 对抗负向控制; 六条规则: 无登记=未验证 / 静态最高只能报 L1 / L≥2 必须负向控制 / 证据必须落盘可复查 / 表述纪律 / 登记表机检) + [docs/verification-registry.json](./verification-registry.json) (机读登记表, 含 `covers[]` 覆盖插件实现) + `src/agent.tests/VerificationFormTests.cs` **6/6 通过** —— 含**自检负向控制**: 注入 5 类缺陷 (缺负向控制/静态冒充运行/证据路径不存在/插件漏登记/等级越级) 全部被抓出。已挂 README + 总纲 §0-0 第 9 条。
- **L2 自上下文能力差异 + 首批修复**: 新增 [docs/plans/v0.22.0-l2-capability-diff.md](./plans/v0.22.0-l2-capability-diff.md) (16 项逐条对位, 判定只用 `file:line` 实证; 缺口清单 G1–G9 入长期看板)。
  - **F1 跨会话检索** `src/agent/session/SessionHistorySearch.cs`: 会话记忆已落盘却**无检索入口** (对位宿主侧 session_search) → 纯 stdlib/零 LLM/确定性打分 (CJK 二元组 + ASCII 词 + IDF + 子串加成), 命中词居中开窗截断; `SessionHistorySearchTests` **10/10** (含负向控制: 无关查询空结果 / IDF 判别力 / **只读保证**: 检索前后 mtime 不变 / 缺文件不抛)。
  - **F2 宣称纠偏**: `skills/critic-rules/SKILL.md` 写的"输出后机器侧静态扫描仍会复核 (双保险)"与代码事实矛盾 (**生产 0 消费**) → 改为真实状态 + 登记"接线"为待办 (诚实优先于好看)。
- **L5 运行级验证 (t8–t12, 用户 5 项计划之一)**: `src/agent.skills/PythonRunVerifier.cs` + `PythonArtifactPlugin` 接线 —— 默认**关** (`AGENTFRAMEWORK_PY_RUN`), 开启后语法通过即真跑并回写 `Ran/RunExitCode/RunElapsedMs/RunTimedOut`; 零 shell (`ArgumentList`), 超时**杀进程树**, 输出上限**排空管道**(否则 300k 输出会假超时), 结构化结果不抛异常。`PythonRunVerifierTests` + 插件接线 **15/15** (含 300k 排空 / 路径含空格与引号 / 闸门关不执行 / 脚本不存在)。
  - **顺带修真缺陷**: 产物命名 `py_<ts>_<sha8>.py` 含时钟 → 同内容跨秒产出两个文件, 破坏"内容寻址幂等"契约 (R368 用例在本机高负载下必红, 属潜伏 flaky) → 改 **纯内容寻址 `py_<sha16>.py`**。
- **L3e 教训表 (exp5 首批, 归属 role 模块)**: `src/agent.roles/` 新增 `LessonGeneralization` (通用化机检: 黑名单词表 + 词法边界, 防误杀) / `LessonTable` (统一记录 + FNV-1a 指纹 + 去重归并 + 版本/增量游标 + STJ 源生成 + 原子写) / `RoleLessons` (role 门面; 无 role 按口径① 不落盘不注入且**显式回报**), 落盘 `data/roles/{roleId}.lessons.json`。`LessonTableTests` **11/11** —— A1 去重计数 / A2 **指纹与独立 Python FNV-1a 实现互锁** / A3 增量游标 / A4+A5① 用户项目目录零新增 / A5② 跨 role 隔离 / A8 正+负 (同通用模式双语实例归并 1 条 Count=2; Pattern 含 `py_compile`/`C#`/`.cs` **一律拒收**)。
- **L4 bge 闲时训练闭环 + 召回实测 (用户本轮新焦点, 关键裁决反转)**:
  - 评测台: 冻结语料 **1299 块/384 文件** + 冻结查询 **120 条** (LLM 生成, 强制不复述片段独特标识符 + ASCII 标识符过滤) + recall@1/5/10/20 + MRR@10 + 词法基线。
  - **实测 (llama.cpp 金标准口径)**: 词法基线 r@1 **0.4417** / r@10 0.750 / MRR 0.5571; **bge-base r@1 0.4417 / r@10 0.7417 / MRR 0.5416**; **bge-small r@1 0.3083 / r@10 0.6333 / MRR 0.4150**。
  - **裁决反转 (诚实更正)**: 10 条硬集上"bge-base 未赢 bge-small"是**样本噪声**; 120 查询口径下 **bge-base 全面领先 bge-small (r@1 +13.3pt)**, 且 ≈ 词法基线 → **纯稠密无优势, 正解是混合检索**。用户钦定基座仍为 bge-small (成本 1/6.6, 内存 106MB vs 193MB), 目标改为"用 T1 适配器把 r@1 从 0.308 逼向 0.44"。
  - **互补性实锤**: bge-small 相对词法 `dense_only_wins=7` / `lexical_only_wins=15` / `both_fail=21`; **union@10 0.7917 (词法单用 0.75, +4.2pt)** / union@20 0.825; oracle@1 **0.5333** (完美选择器上界) → **稠密确有词法够不到的独有命中**, 混合检索有据。
  - 闭环代码: `eval/bge/{bge_lib,collect_pairs,train_adapter,eval_recall,complementarity}.py` (纯 stdlib, 零 shell subprocess, 512 维手写矩阵运算) + `scripts/bge_idle_train.sh` (闲时闸门: load<1.0 ∧ 可用内存≥1.2G ∧ 无在跑任务) + cron `bge-idle-train` (每 30min, 空闲才跑, 无版本产出则零输出不打扰) + 设计文档 exp7。
  - **修缺陷**: ① 缓存 tag 不含模型身份 → 跨模型串用向量 (改 `模型名__前缀_sha_len`); ② llama-server **就绪判定错** (端口可连 ≠ 模型已加载 → qwen3/m3 首请求 503 掉队) → 改为"真发一次嵌入成功才算就绪"。
- **基线**: 单元测试 **772/772** (R368 736) / NativeAOT linux-x64 **0 IL 警告**, `agenthost` **13,792,560 B** (R368 13,775,840 B, +0.12%) / 批测 523 轮 (下轮 524, autopilot 取值自证)。
- **诚实边界**: ① L1 只覆盖已登记项, 覆盖度靠 `covers[]` 机检而非全仓普查; ② L2 的 G1–G9 多数**未接线** (只做组件 + 机检); ③ exp5 前端域登记/`lessons_version` 与三源适配器投影未做; ④ bge 版本小报待首版产出; ⑤ m3/qwen3 召回数字为补跑 (成本维度已淘汰, 不改变选型)。

---

## R368 探索轮: 用户 OOB 5 项计划立项 + PY 落盘/机器校验插件落地 (736/736, AOT 0 IL 警)

- **用户指令 (逐字, 两条)**:
  1. "同步github后继续下轮 并且 新增计划 1.grep本地关键词建索引建立缓存于加载校验能力（需惰性加载）…代码引用索引建立（插件增强服务，需要明确的API规范，要求怎样的数据），全部都建立再一个本质上不主动探索全量（文件索引机制建立插件 返回graph 或 由bge自动建立效果如何？） 2.LLM得到多方案不明确时向用户提出问题menu菜单选择后继续任务… 3. 逻辑校验，修改当前步 看下上一步修改规则对齐当前… 4. agent自动提出需要的工具与工具需求，输入与输出对接参数… 5. 上下文中同类教训/问题记录->应进入教训表…**新增任务全部先列为探索项查找相关数据设计最佳方案后再考虑开发**"
  2. "我需要你对比自身的上下文，并再运行项目agent内 尝试对话 看看再哪个环节 KPI不行，长任务断链，机器验证失败（如PY执行，**你需要自己先内置个PY和先加个PY执行插件**）导致用户某项任务不达预期…着重看看那步应该交给脚本完成agent却又扔给了llm处理"
- **探索产出 (5 路并行只读侦察 + 真机实验 + 本机基准, 未改业务代码)**: [docs/plans/v0.22.0-exploration-index.md](./plans/v0.22.0-exploration-index.md) + exp1…exp5 五份独立文档 (含现状事实带行号 / 候选方案对比 / 推荐 / 关键约束 / 验收标准 / 排除项 / 待确认)。
- **关键发现 (5 条, 皆有代码证据)**:
  1. **头号断链: 框架内不存在"生成脚本"能力** — 两条脚本执行链 (skills `scripts/main.py` / `ScriptPluginRunner`) 都要求脚本**已存在于磁盘**; 任何"帮我写个 X"任务只能一段式由 LLM 在回复里吐代码, 不落盘/不执行/不校验/不可迭代。
  2. **"宣称≠实现"再添 3 例** (R365 同类): `OutputCritic`/`CriticPipeline`/`FormatRepairLoop` 已实现但生产 0 调用, 而 `skills/critic-rules/SKILL.md:82` 声称"机器侧静态扫描双保险"; `TaskCharter.AcceptanceCriteria` 0 消费方; CLI `(已路由插件)` 文案无对应校验动作 (**本轮删除该空话**)。
  3. **前端通知层缺失** (探索项 2/5 共用瓶颈): `FormatEvent` 有信封零调用, 域枚举只 3 个, `state.snapshot` 不含 lessons, 无订阅/游标 → "新教训已到达"当前**不可能送达**。
  4. **跨步产物不落不传** (探索项 3/4 同根因): runner 签名忽略上游产物 + 步骤产物不持久化 + 恢复只恢复状态 → 长任务跨步只能靠上下文猜。
  5. **bge 全量索引不可行 (本机实测)**: bge-q8 CPU 单线程 203.5 ms/块 / 4.9 块/s / RSS 306 MB → 全仓 6375 块 ≈ **21.6 min** → 与用户"不主动探索全量"直接冲突。
- **本轮实施 (探索项 4 的 T1/T2/T3)**:
  - `src/agent/registry/PythonArtifactPlugin.cs` (新增): ```` ```python ```` 段 → 落盘 `data/artifacts/py_<sha16>.py` (内容寻址幂等; **R370 修正**: 旧名 `py_<ts>_<sha8>.py` 含时间戳 → 同内容跨秒会写两个文件, 与幂等契约冲突, 本机高负载时用例必红) + 真实 `python3 -m py_compile` 机器校验 + `PythonArtifactLedger` 台账 (线程安全, 单调 Version, 供前端增量读) + telemetry 点 `script_artifact`; **输出恒等** (不改写 LLM 文本/围栏); 非 python 段零损耗透传; `AGENTFRAMEWORK_PY_ARTIFACT=off` 可关。
  - 接线: DI 注册 (`ServiceCollectionExtensions.cs:150-158`) + CLI 步骤 `[05] PY 落盘 + py_compile N/M 通过` (`Program.cs:490-518`)。
  - 零 shell 修复: `PythonScriptValidator` `Arguments` 字符串 → **`ArgumentList`** (跨平台铁律); 新增 `ValidateAsync(path, pythonPath, ct)` 重载使 `AGENTFRAMEWORK_PYTHON` 覆盖真正生效。
  - 测试: `PythonArtifactPluginTests` 6 用例 (好码落盘+过 / 坏码失败不静默 / 非 python 透传零副作用 / 同内容幂等 / 版本单调 / 路由器集成原文还原)。
- **真机对照证据 (同一句话, 同一模型 `deepseek-flash`)**:
  - 改造前: `intent=general`, LLM **1 次** 12990 ms / promptTokens=642, **无文件、无校验**, CLI 显示 `(已路由插件)` 实为空话。
  - 改造后: CLI `[04] 返回区段标记 python` → `[05] PY 落盘 + py_compile 1/1 通过`; 产物 `./data/artifacts/py_20260913_035648_1f3f027c.py` (4573 B / 137 行); telemetry `{"point":"script_artifact","compile_valid":true,"exit":0}`; **独立复核** (不信 agent 自述): 另跑 `python3 -m py_compile` → exit 0 ✓, `ast.parse` 通过。
- **附带修复 (同步上游后发现)**: 同步远端 R366/R367 后全量测试出现 1 例失败 `LlmServiceTests.ConcurrentClients_SpawnOnce`。定位为**真竞态** (非环境噪声): 启动锁只在启动期持有, 抢锁者释放后, 另一客户端到达 `CreateNew` 时见锁已消失 → 判 stale → 重新抢锁并**冗余 spawn** (生产=第二个 daemon 白启后退出码 4; 测试=fakeSpawn 抛"已在运行"致断言崩)。修复: 抢到锁后**再复检一次探针**, 已就绪则释放锁直接复用。复现基线 6 并发 1 失败 → 修复后 **10/10 通过**。
- **基线**: 单元测试 **736/736 全绿** (730 + 6 新增); NativeAOT `linux-x64` **0 IL 警告**, 二进制 **13,775,840 B (13.78 MB)**, 体积同比 +0.18%; **AOT 冒烟真机真 LLM 通过** (`E2E: Success=True` / `Multi-turn round2Success=True` / `full-graph AOT smoke passed`)。
- **诚实边界**: ① 校验仅**语法/编译级** (py_compile), ≠ 逻辑正确, 文档已明写, 不许表述为"已验证可用"; ② 运行级验证 (沙箱+超时+stderr 回灌修复环) **未实现**, 列为 T4/T6 待开发; ③ 探索项 1/2/3/5 全部为**探索态文档**, 未写实现代码; ④ 侦察中的不确定项 (失败簇"超时/停滞"调用点未找到、`CommandWriter` 是否他处接线) 原样保留在各文档 §待确认, 未粉饰。


## R367 v0.21.1 候选 samples WinForms 前端对接 DEMO + FrontendApi 内部问题修复 (提交待 CI 复核)

- **用户指令 (逐字)**: "建立 samples 内创建前端对接 agent.frontendapi 的 UI 项目使用 winform 来做对接 DEMO 查找和继续优化 agent 内部问题"。
- **samples/FrontendApi.WinForms (新增)**: WinForms (`net10.0-windows`) 最小可运行前端, 经 TCP 行 JSON 消费完整 agent 管线。
  - 协议严格对齐实现: 鉴权首行 `{"type":"auth","token":"..."}` / 请求 `{"v":1,"type":"req","req_id","api","payload"}` / 响应回显 req_id / `event` 单向信封 / 错误码 `unknown_api|bad_payload|busy|conflict|not_found|internal`。
  - 功能: `chat.send` (直通 V2 管线) + `state.snapshot` / `state.hello` / `meta.info` / `meta.ping` + **原始协议日志面板** (>> 发送 / << 接收, 排查主手段)。
  - **刻意不入 `agent.sln`**: 仓库 CI 跑 `ubuntu-latest` 且 `dotnet build -warnaserror`; `net10.0-windows` 进 sln 会因 Linux 无 WindowsDesktop 引用包而**构建失败**。仅 Windows 单独 `dotnet run`。
  - 客户端兼容: 旧服务端限流 `req_id` 恒为 `"rate"` 无法关联 → DEMO 退化为"完成最早未决请求", 避免界面永久挂起。
- **本轮揪出的内部问题 (5 项, 前 4 项为真实缺陷, 已修)**:
  1. **限流响应 `req_id` 硬编码 `"rate"`** (真缺陷): 违反契约"响应回显 req_id", 客户端无法关联被限流的请求 (只能靠顺序推测)。→ 改为回显真实 `req_id` (信封非法时用 `"unknown"`); 顺带把限流准入移到解析之后, 非法信封不再白占令牌。
  2. **`chat.send` 缺 `text` 被误判为 `internal`** (真缺陷): `FrontendApiChatRouter` 抛 `BadPayloadException`, 但 `ServeClientAsync` 的 catch-all 把它吞成 `internal`, 与契约已定义的 `bad_payload` 语义不符 (前端无法区分"参数错"与"服务端炸了")。→ 在 `ServeOneLineAsync` 显式捕获并映射 `bad_payload`。
  3. **请求行缓冲 `pending` 无上限** (真缺陷): 客户端持续灌入**不带 `\n`** 的数据 → StringBuilder 无界增长 (内存 DoS)。→ 加 `MaxPendingBytes = 1MB`, 超即断连。
  4. **鉴权握手 `sb` 无上限** (同类缺陷, 更隐蔽): 原 `line.Length > 4096` 检查**只在找到 `\n` 之后**才生效, 未遇换行前可持续增长; 且 auth 阶段位于限流/并发准入**之前**, 5s 窗口内可大量灌入。→ 加 `MaxAuthBytes = 8KB`。
  5. **`meta.info` 版本漂移**: 硬编码 `"0.20.5"` (实际 v0.21.0), 前端无从得知真实版本。→ 校正为 `"0.21.0"` (无单测依赖该字符串; 测试用的是自身 `metaInfo` 注入值)。
- **观察项 (设计如此, 不改)**: ①鉴权失败 = **静默断连** (防枚举探测), 客户端只能靠"首个请求即断连"间接判定 → DEMO 已针对性提示"疑似 token 错误"; ②`FrontendAccessControl` 全局 **10 req/s + 并发 4**, `chat.send` 单次耗时长, 连续发送易触 `busy` → DEMO 提示限流原因。
- **基线**: 现有 `FrontendApiTests` 4 用例 (信封解析 / 真 TCP 往返 req_id 回显 / unknown_api / bad_payload) **均未断言 `"rate"`**, 改动不破坏; 新增代码为纯增量。
- **诚实边界**: 本沙箱无 .NET 10 SDK 且 nuget/builds.dotnet.microsoft.com 被封 → **未本地构建/未跑单测**; WinForms 项目须 Windows 构建, 本沙箱 (Linux) **无法运行验证** (仅源码级对齐实现与契约)。全部改动经人工逐行复核为 AOT 安全增量, 待仓库 CI (build -warnaserror + test + AOT publish) 全量复核后再落版本戳。

## R366 v0.21.1 候选 DeepSeek 内部用例测试 + 推理模型思考链捕获 (提交待 CI 复核)

- **用户指令 (逐字)**: "使用 token 阅读文档后不断完善 click-agent 项目; 内部用例测试用的 deepseek api: sk-…"。
- **DeepSeek 内部用例测试探针 (probes/deepseek-probe, 新增)**: 不依赖 NativeAOT 构建, 用真实 DeepSeek API 验证 `src/agent.modelqueue` 发出的 OpenAI 兼容 chat/completions 请求契约, 并捕获项目 DTO 未解析字段。凭据铁律: key 仅从环境变量 `DEEPSEEK_API_KEY` 读取, 输出脱敏; 内置 1.5s 调用间隔 + 对 401/429/5xx 指数退避重试 (规避 DeepSeek 速率窗口)。
- **推理模型思考链捕获 (v0.21.1 核心)**: 实测证实项目首选 `deepseek-flash` **即推理模型** (返回 `reasoning_content`), 而 `OpenAIChatResponseDtos.cs` 此前未解析该字段 → 思考链整段丢弃。补:
  - `OpenAIChatResponseMessage.ReasoningContent` (`[JsonPropertyName("reasoning_content")]`, 经 `OpenAIChatResponse` source-gen 上下文自动纳入, AOT 安全);
  - `QueueResponse.ReasoningContent` + `CallEntryAsync` 捕获 `choice.Message.ReasoningContent`;
  - `LLMResponse.ReasoningContent` + `ModelQueueAdapter` 透传;
  - 三处 `llm_call` 遥测补 `reasoning_len` (主成功/请求内重试/兜底切换路径一致)。
  - 纯增量, 无反射/无新类型注册, 不破坏 AOT 零 IL 警告契约。
- **models.yaml 校正**: `balance_schemes.deepseek` 旧注 "balance 字段 USD" 实测为 **CNY** (`balance_infos[].currency=C NY` / `total_balance`) → 校正注释; `deepseek-flash` 条目补 "推理模型, 返回 reasoning_content" 说明。
- **实测契约结论 (真实 key, 探针 6 用例)**:
  1. `deepseek-flash` = 项目发送的真实模型名, 接受且返回 `reasoning_content` (推理档 low/high 思考链长度随档增长) ✓;
  2. `deepseek-chat` 非推理, 无 `reasoning_content`; 收 `reasoning_effort` 被无害忽略 (200) ✓ — 项目对全模型透传 `reasoning_effort` 安全;
  3. `deepseek-reasoner` 历史推理模型, 可用性随 DeepSeek 目录变动 (探针保留该用例);
  4. `GET /user/balance` 返回 `balance_infos[].currency=C NY` (非 USD) ✓。
- **观察项 (未改动 auth 语义)**: DeepSeek 对 chat/completions 速率窗口返回 **401 而非 429**; 项目 `OnTransientFailureAsync` 仅把 429 当可重试限流, 401 被当作鉴权硬失败不重试 (真实 401 须 fail-closed, 故不改)。探针已用退避重试规避该窗口。
- **基线**: 真实 DeepSeek 调用 6 用例契约验证通过 (reasoning/reasoner 视目录可用性); 改动 `git diff` 纯增量。
- **诚实边界**: 本沙箱无 .NET 10 SDK 且 nuget/builds.dotnet.microsoft.com 被封 → **未本地跑 730 单测 / NativeAOT 构建 / eval**; 改动经设计评审为 source-gen 安全增量 (仅新增可序列化属性 + 遥测字段), 待仓库 CI (dotnet build + test + AOT publish) 全量复核。版本戳 (csproj 0.21.0→0.21.1 / README 徽章) 待 CI 绿后由统一提交补齐, 避免未构建即改版本号造成口径不一致。

## R365 v0.21.0 Role 系统交付 + 凭据加密 + FrontendApi 鉴权 (批523 13/13, 提交 `7ed4031`)

- **用户指令 (逐字)**: ①"凭据静态加密 请用跨平台统一方案" ②"完善 6 个硬缺口" ③R360 "不做前置人格语料，倾向=对用户问题置信度的赏罚涌现" ④R361 "用对抗用例验证后有效在接近V2 并记得 role 可以外挂依据给 V2" ⑤**R363 "去掉roles目录相关，仅能外部挂载单文件且不可是明文，需压缩友好的快读快写可扩展结构，提供API读取修改写入 并实现 ① 推理中止→失败簇三件实现 ② 赏罚信号接 V2 主链（:1270 替换 llmResponse.Success）"** ⑥"全部提交github，并更新全部文档到当前项目状态"。
- **凭据静态加密 (R358)**: 新建 src/agent/CredentialEncryption.cs — **AES-256-GCM**（跨平台统一原语，AOT 全支持；不用 DPAPI/libsecret 分叉）；master.key 32B 落盘 600 权限；明文自动迁移（Load 兼容 + 首次 Save 即加密）；GCM 篡改拒绝。PromptPersistence 接入；6 单测。
- **Role 单文件 `.rbin` (R363, 用户钦定修订)**: 新建 src/agent.roles/RoleBinaryFile.cs（191 行）— 16B 头（magic `ARBL`+version+flags+压缩长度+原始长度）+ `AES-256-GCM(gzip(JSON))`；密钥=`data/master.key` 持久层级（跨会话可解/换机不可解）；未知 `x:` 前缀键读写往返保留（可扩展）；tmp+rename 原子写；Read/Write API。**目录方案废除**：RoleRegistry.cs 删（照 SkillRegistry 的 roles/ 目录包扫模式终弃），Program `--role` 改接 .rbin 路径、`--roles-dir` 删。实测 700B 文本 → **306B**；hex dump 仅见 magic + 密文（非明文实证）。
- **赏罚涌现倾向 (R360, 用户钦定非前置语料)**: CorrectionDetector.cs 两级判定 — L1 规则词面（"不对/错了/不是这个意思"等强模式，**0 token**，14 轮模拟拦 12/14）+ L2 微 prompt（**单字母 C/A/N 输出协议**，~140 tok/次，均摊 20.7 tok/轮，省 85%）→ RoleGrowthLedger.cs 域级 Beta 计数，confidence=(赏+1)/(总+2)（Laplace），**<0.4 先怀疑 / >0.7 信任 / 样本<5 观察中**。实证：docker 域 5 罚 0 赏 → 0.143 Distrust（"先怀疑"自动涌现）；git 3 赏 0 罚 → 0.800 观察中；跨会话重载保持。
- **推理中止→失败簇 (R364, "三件")**: FailureClusters.cs — 中止检测（超时 / token 超限 / **自证循环**：窗口 3 轮回复 trigram Jaccard ≥0.95 判原地打转）→ 问题指纹簇归类（落盘跨会话）→ **罚分 ≥3 前置注入**策略警告（先澄清/降级/诚实坦白）。Jaccard 修 `last.Count(prev.Contains)` 歧义为 `last.Count(t => prev.Contains(t))`。
- **R365 文档同步期审查（自查发现 3 真缺陷，已修）**: ①**前置注入实际未接线**——`RenderWarning` 有实现但 V2 prompt 组装处从未消费（"三件"只有两件在跑，属宣称与实现不符）→ 接入 Role 块（`message.Content` 指纹命中且罚分≥阈值 → 注入），无 role 时不进分支；②**簇键跨进程不稳定**——`string.GetHashCode()` 在 .NET Core 对 string 每进程随机化种子，落盘的 `failureClusters.json` 重启后键全失配 → "跨会话簇归类"静默失效（同进程测试测不出：`落盘重载_簇保持` 恰好骗过）→ 改 **FNV-1a 32bit 自实现**；③**指纹排序文化相关**——`List<string>.Sort()` 默认文化比较，同问题换 locale 得不同键 → 改 `StringComparer.Ordinal`。新增回归锁 `簇键_进程间稳定`（硬编码 3 键值，期望值由独立 Python FNV 实现交叉验证，非抄实现输出）。
- **赏罚接 V2 主链 (R364)**: CorrectionDetector 后台 Task（不阻塞响应）挂记忆回写区，`GrowthLedger.Record` + LLM 失败 → `FailureClusters.RecordAbort`；L2 判定走模型队列 ContextCompression 通道（微 prompt 隔离）。
- **无 role 门禁 (用户 OOB 校验令)**: 查实 2 处漏洞（纠正检测 Task 无 role 仍起 → 白烧 LLM token；失败簇仍写盘）→ 加门禁：`GrowthLedger == null` 整链失效 — 不起 Task / 不调 LLM / 不写盘 / 联想前置注入关闭（null 安全空返回）；无角色行为与 v0.20.5 一致。
- **对抗验证 (R361)**: /tmp/adversarial 30 例（判罚正例10 / 判赏正例8 / 误杀陷阱7 / 模糊灰区5）；首轮 23/30 → 修 L1 语境豁免（转述/假设/历史）+ L2 单字母协议 + max_tokens 自适应重试（deepseek-flash 是 reasoning 模型，思维链吃光 token 致 content 空）→ **30/30（判分题 25/25 = 100%）**；固化 CorrectionDetectorTests.cs 22 用例（脱 LLM，L1 规则 / L2 mock）。
- **FrontendApi 鉴权 + 限流 (sec2/sec3 部分)**: FrontendAccessControl.cs（共享 token：随机 hex 或 env 注入 / 令牌桶限流 / 并发上限）。
- **真机 E2E**: `agenthost --frontend-api 47819 --role skeptic.rbin` → 同对抗问题回复"前提澄清: 没有证据表明…"（人格从加密单文件加载，4.2s）✓；R355 TCP 47812 chat.send E2E（meta.ping→pong / "回复两个字:收到"→"收到" / 未知 api 结构化错误）。
- **基线**: **730/730 全绿**（729 + 1 新增回归锁 `簇键_进程间稳定`；R362 为 718）；AOT **13.75MB** 零 IL 警告；批 523（DS 主力首测）13/13。
- **诚实边界**: ①R2 能力绑定（Role 绑独立二级召回源）未实施；②`/role` 指令族未做（改 `--role` 启动参数 + `role.info` api）；③embedcpu 无关对 cos 0.90+ vs llama.cpp 金标准 0.18-0.23 差异未解（Q8_0 地板假设已证伪）；④sec2 鉴权仅 token，OAuth/mTLS 未做。

## R355/R356 v0.19.0 FrontendApi chat 域接通 + DS 主力切换 (批 523 13/13, 提交 `3f90e3c`/`6a33404`)

- **用户指令**: ①"若当前你通过API使用LLM服务是GLM请改成DS, ds-flash4.1" ②"② KPI token 口径决策 ③ FrontendApi state.snapshot 真实状态填充"。
- **R355 FrontendApi chat 域**: 新建 FrontendApiChatRouter.cs（chat 域异步 handler 持 IAgent，直通 ProcessAsync）；FrontendApiServer handler 签名升级 `(api, payload)`；Program 加 `--frontend-api <port>` 第三运行形态（TCP 常驻）。两处 AOT/契约级修复：payload 透传缺失（server→router 传 "{}"）、AOT 反射禁用下匿名类型序列化崩溃 → 手写 Utf8JsonWriter。真机 E2E 全通；677/677，AOT 13.4MB。
- **R356 DS 主力切换（二分实证）**: 修前真相 = **首选实为 GLM**（打分 GLM/DS 同 8 分，GLM 价格 0 → fitness×2+推理×3+编码×3-价×2 恒胜；models.yaml "首选"标注仅注释、代码不消费）。修 A：models.yaml 加 `priority`（DS=1/GLM=2），ModelSelectionPolicy 每低一档 **-5 分**压过 0 价优势；性能不敏感分支（压缩/标注）同锁首选；未声明=旧行为不变；6 单测含"未声明时 GLM 仍胜"回归保护。修 B（正名）：**`deepseek-4.1-flash` API 名不存在（400）** → 官方支持名 = **`deepseek-flash`**（另一合法名 deepseek-v4-pro），直调 200 model echo 确认。终验：GLM 坏 key 下 chat.send **一次成功、零 401、零兜底、零 warn**。683/683。
- **R356-b embedcpu 数值审计（llama.cpp 源码对照）**: curl 拉 llama-model.cpp / llama-graph.cpp / src/models/bert.cpp / ggml.c 逐项对照 — 前向 8 项对齐 bert.cpp（gelu=tanh 变体、无 causal mask、scale、残差位置全 ✓）；**修正 pooling：mean→CLS**（BGE 官方 1_Pooling 实证 cls_token + pooling_type=2 是转换器默认值不可信）；WordPiece 去 ▁ 前缀（BERT 词表无 ▁，词="word"/子词="##sub"）→ **相关对 cos 0.8372 → 0.9634** ✓。683/683，推 `a8fe11f`。
- **llama.cpp 金标准对照（决定性实验）**: ghfast 镜像 clone llama.cpp 11s → 构建 llama-server（新版 embedding CLI 已移除，改走 `/v1/embeddings`）→ 同 `bge-q8.gguf` 加载：**mean pooling 无关对 0.17-0.19，CLS pooling 0.18-0.23 vs 我们 0.90+** → **Q8_0 噪声地板假设证伪，前向仍有差异（未解）**；同句前 16 维 cos 0.79。
- **R356-c**: KPI token 口径重锚（tokens_per_case 上界 1300，批 523 实测 1836 带外待定夺）+ state.snapshot 真实状态填充。
- **基线**: 683/683；批 523 = **13/13**，1836 tok/case，8.0s/case（DS 主力首测）。

## R353/R354 v0.20.5 模型通道精简 + bge 本地 CPU 最小推理 + LLamaSharp 全拆 (批520/521/522)

- **用户指令**: ①"去掉项目内本地加载本地llm与官方llm相关功能…仅保留api调用能力" ②"deepseek4.1flash首选 glm5.3flash次选 保留gpt6默认 其余model预留配置移除" ③"去掉llama后仅限cpu 不要onnx 少量代码或成熟库" ④"bge即便用最小实现也请本地cpu异步跑" ⑤"脚本互动若业界无先例则删" ⑥"跨平台vector实现"。
- **通道精简**: 删 LocalLlamaCaller/LocalInferenceAdapter/ILocalInference/OfficialModels/OfficialKeyStore/--official-key; ChannelScheduler 三通道→单 Remote; models.yaml 52→3 (deepseek-4.1-flash 首/glm-5.3-flash 次/gpt-6 默认配置); core.yaml model gpt-4→gpt-6; SkiaSharp 渲染器删 (仅 SVG)。
- **LLamaSharp 全拆** (vendored fork 445MB 目录+nuget 缓存+csproj 引用+native 复制段): BgeEmbedder/SharedEmbedderRegistry/BgeEmbeddingProvider 删; qwen/bge-small-en gguf 删 (bge-q8 保留 — embedcpu 引擎)。
- **embedcpu 新项目** (纯托管零原生依赖, ~470 行): GgufModel (GGUF v3 最小解析+Q8_0/F32 反量化+f16 手写位运算) / WordPieceTokenizer (21128 词表最长匹配+## 子词回退+中文按字) / BgeCpuEmbedder (4 层 BERT forward, TensorPrimitives SIMD, mean-pool+L2, 惰性双检锁, EmbedAsync=Task.Run 异步)。
- **真 bug (R353b 修)**: Q8_0 反量化 Data.ReadByte() 返回无符号 int → 负权重变正大数 → cos 恒 1.0 嵌入无区分度; 修 = (sbyte) 显式转换; 修后与 python 参照逐位一致。
- **R353c 跨平台向量化** (用户检查点): 剩余 4 处标量循环全 TensorPrimitives 化 (embedding 查表/attention 加权/SoftMax/LayerNorm 仿射) — 跨平台自动 SSE/AVX2/AVX512/NEON。
- **R354 eval 同步**: LOCAL_DISABLED 死开关退役 (本地通道本体已删, R107 泄漏源不存在); D4 gate 不再依赖 BGE_MODEL (--embed 走 llm-service), 自动探测 agenthost 路径注入 LLM_SERVICE_BIN。
- **真缺陷 (520/521 双 0/13 负样本如实)**: 清 bin/obj 后未重建 host 而 run_round 用 --no-build → CLI 不存在全 case 650ms 空回; 重建后 CLI 手验 glm-5.3-flash 正常回复。教训: 清 build 产物必须立刻重建 host (run_round --no-build 依赖磁盘二进制)。
- **脚本互动调研归档** (R352-d): 8 家主流 agent 均无"脚本执行中主动问 CLI"先例, 主导模式=单向事件流 → 本项目 ScriptPluginRunner 单向事件流判定保留 (script-interaction-research-R352.md)。
- **基线**: 677/677 绿; AOT 13.4MB 0 IL 警告; bge CPU 热嵌入 ~26-90ms; 验收批 522 (host 重建后)。

---

## R343 v0.20.0 LLM 服务独立进程 — llm-manager / worker 架构 (批516 quick-13 验证中)

- **用户指令**: "将llm服务写成单独进程, 以免新CLI重新加载LLM到显存内, 最好使用小而完善的框架完成"; 纠正 "仅是新增本机 llm host 而非全面修改当前框架llm使用流程"; 钦定策略 "一个是 llm-manager 进程, 一个是实际 llm-service-host; **卸载直接杀 llm-service-host 就好了**"。
- **现状代码事实**: BgeEmbedder (llamalocal) 惰性加载 bge-q8 26MB (加载后 RSS ~157MB 实测), 每 CLI 进程经 DI 新建 (ServiceCollectionExtensions L226); LLamaEmbedder.Dispose() 只释放 Context **不释放 _weights** (LLamaSharp L54-57 实测) → 手工卸载需穿透 SharedEmbedderRegistry (无卸载 API) + 引用计数, 复杂易漏; CLI 生命周期 = REPL while(true) (L296) 或 -q 单次, 多实例并存。
- **架构**: `llm-manager` (轻量常驻, 0 模型, 不随 CLI 生死) 对外 UDS 透明代理 → lazy spawn `llm-service-host` worker (真 bge); 卸载 = kill worker (OS 回收全部 native 内存, 绕开手工释放/引用计数)。ping 由 manager 直答 (探活不触发加载); 双启保护 .manager.pid/.worker.pid; 客户端 .startlock 原子抢占; SIGKILL 后孤儿 worker 由新 manager 清理。
- **卸载判定 (纯函数, 单测矩阵)**: `ShouldUnload = workerUp ∧ inflight==0 ∧ availMb>0 ∧ availMb<floor(512) ∧ cliCount==0` — **不按时间** (用户钦定: 内存充足常驻); **空闲长连接不阻止卸载** (实测缺陷修正: 原含 conns==0 导致 CLI 长连接永久阻止卸载); 读不到内存 (非 Linux) 保守不卸。
- **跨平台 (用户 OOB "/bin/sh 跨平台怎么办?")**: 产品代码零 shell — spawn 用 `Process.Start`+`ArgumentList`, 卸载用 `Process.Kill(entireProcessTree:true)`, 存活判断 `Process.GetProcessById`+`HasExited`; daemon 自写日志 (env LOG, 替代 sh 重定向); UDS 跨平台 (Win10+ AF_UNIX); /proc/meminfo 非 Linux 优雅降级 (Windows GlobalMemoryStatusEx 待办)。
- **验收**: 新增 LlmServiceTests(9)+LlmManagerTests(7) → **全量 661/661 绿**; AOT publish 13.6MB **0 IL 警告**; 真机 E2E: ①manager READY 0 模型 → ②首请求 lazy worker (RSS 157684KB, bge 512 维) → ③kill -9 worker → ④下请求自动重拉 (pid 2659546→2659594) + manager 存活 → ⑤阈值拉满+无 CLI 实例 → worker 被卸载无残留。
- **诚实边界**: ①RemoteEmbedder 尚无框架内调用点 (opt-in 集成 = v0.20.1 P4-a); ②worker 仅服务 bge embed, 本地 LLM 推理未 worker 化 (P4-b 评估); ③Windows 内存探测未实现。

## R338 v0.17.3 P10 锚词 Span 化收尾 (批288 quick-13 13/13)

- **立项**: improvements.md 下轮候选 — R333 (v0.16.4) 完成 P10 中文 2/3/4 字窗 long-key 零分配后遗留 **English 段未动** (function-map-R326 P10: 压缩热路径锚词提取)。可选性: c 收口/dormant 退役均需用户裁定 → 本轮唯一可执行候选。
- **现状代码事实** (src/agent/contextassembler/ContextAssembler.cs, ExtractAnchorWords L1006+): CJK 窗 R333 已零分配; English 段仍 `Regex.Matches(content, "[A-Za-z]{3,}")` + 每匹配 `m.Value.ToLowerInvariant()` = **每 English 词 2 次短串分配 + MatchCollection/Match 分配**; 压缩热路径每超限 snippet 触发一次 (代码/英文片段词数×2 分配)。
- **修法**: English 提取 → `Regex.EnumerateMatches(content.AsSpan())` (零 Match 对象) + **≤7 字符词 8bit/char long 键零分配计数** (ASCII 字母 `|0x20` 即小写; 8×7=56bit 键域无歧义; 字母编码无中间零字节 → decode 移位归零即末字节; 复用栈槽免 CA2014); >7 字符词 string 兜底 (长词稀有); 两路 distinct 首见登记 enOrder (枚举序=match 序=内容首见序), 计数毕按登记序解码 count≥2 候选入 words — 与原实现 (English match 序先、CJK len-major 后) **同插入序**, count 相同下稳定排序输出全等。
- **验收**: **624 单测绿** (+5 ExtractAnchorWordsEquivalence InlineData: R333 随机语料英文词全 ≤7 字符未覆盖 >7 兜底路径 — 补 >7 重复/短长混合首见序/7-8 边界同 count 保序/>7 大小写折叠/7 大写折叠×8 string 交替); AOT publish agenthost 13.5MB **0 IL 警告** (仅预存在 CS0649/CS0169/xUnit1030); 批288 (round 515) quick-13 **13/13** tok/case 1806 (KPI_BREACH 带外 — C19 重案 8023 tok 已知方差同 R337/R331 判型, 通过率主口径零回归; 改动为压缩路径纯函数不进 LLM 链)。
- 收益: English 主路径 (≤7 词, 绝大多数) 每匹配 2 短串+MatchCollection → **零分配**; >7 仅兜底; 与 R333 CJK 段合拢 P10 "单遍扫描 + Span/字典" 全部建议。
- 诚实边界: 片段级锚词缓存 (function-map P10 建议) 未做 (收益需跨 snippet 重复片段真实命中分布, 候选中); >7 词每 occ 仍 Substring+ToLower 与旧版同 (未回退)。
- 下轮候选: c 收口 (/schedule 持久化 + 外部 cron 挂钩 + 定时 skill — 需用户裁定) / 片段锚词缓存 (需命中分布) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需裁定)。

## R337 v0.17.2-b/c 脚本插件协议 + 条件定时 (批287 quick-13 13/13)

- **立项**: 用户钦定 (执行层自需脚本一律 py 编写 → CLI 验证 py 正确后交插件服务执行; 明确对接协议: 定期反馈/结束前返回/长执行心跳) + plan docs/plans/v0.17.2-activity-script-plan.md §2/§3 (b 脚本插件协议 + c 条件定时, 依赖 a 的 IsOtherAgentBusy 条件原语)。
- **协议层** (src/agent.skills/): ScriptPluginProtocol.cs — **JSON Lines 事件流** `{"type":progress|checkpoint|heartbeat|done|error,"ts","msg","data"}`; done/error=权威终态 (以事件为准, 进程退出码仅兜底); done 回填 summary + data.outputs(产物路径); 非 JSON/未知 type 行=调试噪声 (忽略计数); ts 容忍 epoch 秒/毫秒; ScriptEventStreamParser 状态机 (时钟注入): 事件驱动活性 → >2×heartbeat 无事件=疑似挂起判定。PythonScriptValidator.cs — **py_compile 验证门** (真实 `python3 -m py_compile`, 进程级 AOT 安全): 失败=拒绝执行 + 教训 `script-invalid:<name>` (ExecutorLessonMemory 频率加权)。
- **执行器**: ScriptPluginRunner.cs — 验证通过 → task-json 落盘 data/script-plugin/tasks/ (源生 STJ 序列化, 用后即删) → `python3 script --task-json <file> --heartbeat-secs N` (PYTHONUNBUFFERED 强制流式) → 事件流消费 → 活性监控 (疑似挂起打点一次不杀) → 总超时杀进程树返回失败 → 进度/心跳计数打点 + 结束回填。条件定时: ConditionalScriptScheduler.cs (v0.17.2-c) — "如果当前没有其他任务存在则 XX 后执行 Y": 延时到期 → 轮询其他 agent 忙 (接线方注入, 默认 ActivityService.IsOtherAgentBusy 自身排除) → 空闲即执行/忙重试至 give-up; 重试/放弃窗口全走配置委托, 延时/时钟可注入。
- **接线**: /schedule-run <延时秒> <py路径> [目标描述] 本地指令 (LocalCommandRouter + V2 特判臂 0ms 拦截, 坏 py 拒绝+教训落盘 ExecutorLessonMemory.Default; v1 延时上限 60s)。
- 验收: **619 单测绿** (+18 ScriptPluginTests: 解析终态/噪声容忍/秒容忍/挂起活性重置/真实 py_compile 好坏/真实 python3 子进程 done 回填+error 权威+协议违例+静默超时挂起观测+坏 py 真实教训 store 落盘/条件调度 空闲执行·忙拒绝·验证拒绝·取消 — 注 R336 文档 597 为其时计数口径, 含 Theory 行差异); AOT publish 0 IL 警告 (仅预存在 NU1510 包引用提示); **E2E 真机 AOT host 双场景**: /schedule-run 0 好脚本 → ✅ 完成 (200ms 事件3 心跳1, 产物回填 data/script-plugin/outputs/) / 坏 py → ⛔ 拒绝未执行 + `script-invalid:e2e_bad.py` 教训真实落盘; 批287 (round 514) quick-13 **13/13** tok/case 1641 (低于近4轮 1672-1811, KPI_BREACH 带外系 C19 重案 7680 tok + LLM 方差已知现象, 通过率主口径零回归 — 本改动为惰性本地指令+未触发库, 不进 LLM 链)。
- 诚实边界: /schedule-run 为轮内阻塞式 ≤60s v1 (长延时交互语义、跨重启持久化、Hermes cron 挂钩、定时任务 skill 面 = 下轮候选, 交互语义待用户裁定); 脚本产物默认写 data/script-plugin/outputs (改用户文件走 v0.17.1 staging 属接线方职责, 本期未接)。
- 下轮: c 收口 (/schedule 指令面持久化 + 外部 cron 挂钩 + 定时 skill) / P10 锚词 Span 化 / dormant 退役 (需用户裁定)。

## R336 v0.17.2-a 活动任务注册表 (批286 quick-13 13/13)

- **立项**: 用户钦定 (获得所有激活窗口活动任务/其他 CLI 状态/job_id 通知/"无其他任务则 X 后执行"原语) + plan docs/plans/v0.17.2-activity-script-plan.md (a 活动注册表 / b 脚本插件协议 / c 定时 skill 分期)。
- **ActivityService** (src/agent/activity/): 每活动 CLI 进程心跳文件 data/activity/<pid>.json (AtomicFileWriter; 退出 finally ClearActivity + 崩溃由 TTL 兜底); 条目含 pid/window(env AGENTFRAMEWORK_WINDOW)/job_id(env AGENTFRAMEWORK_JOB_ID)/agent/任务摘要/心跳; 查询扫目录; 过期 TTL **90s** (E2E 实证教训: 心跳为轮级非定时器, LLM 单轮 30-60s, 10s TTL 误清在跑实例); IsOtherAgentBusy(自身排除) = "无其他任务" 条件原语。
- **接线**: V2 OnProcessAsync 轮首 Heartbeat(message.Content); Program.cs finally ClearActivity (守护轮并行补); /activity 指令 (Known+switch 臂+V2 特判 0ms 渲染列全部激活 agent: pid/win/job/status/心跳龄/任务)。
- 验收: **597 单测绿** (+6 ActivityService: 注册查询/过期清理/自身排除/多实例无串扰/渲染含 job_id/损坏容忍); AOT 0 IL 警告; **E2E 双实例真机**: 实例 A (win-A/job-A-test/长任务) 运行中 → 实例 B /activity 看到 A: pid/win=win-A/job=job-A-test/任务摘要 ✓ (首版失败=TTL 10s 误清, 改 90s 复绿); 批286 (round 513) quick-13 13/13 tok/case 1811。
- 下轮: v0.17.2-b 脚本插件协议 (py 验证→插件服务执行, JSON Lines 事件流/heartbeat/done 约定) + c 条件定时 (IsOtherAgentBusy 已就绪)。

## R335 v0.17.1 离线变更 + 用户审批 (批285 quick-13 13/13)

- **立项**: 用户钦定 (Q1-Q7: CLI 产出需审批/VS Code 编辑保护/不能停/落盘不占真实地址/下次打开恢复/过期周期/前端取得/多批合并) + plan docs/plans/v0.17.1-staged-approval-plan.md (逐问题设计)。
- **存储**: src/agent/staging/ — StagedFileStore (批次 content 原样落 data/staged/<batch>/<n>.content **不占用真实文件地址**; index.json 原子写; 恢复=新实例读 index; 过期三阶段 TTL→expired(内容保留可取回)/TTL×2→reclaimable/显式 cleanup 物理删 — 不静默丢); ChangeBatch/StagedItem (基线 sha256 快照模型); StagingSha (IncrementalHash AOT)。
- **审批**: ApprovalController.Apply = LockedFileWriter.WriteIf **锁内基线比对** — 用户/编辑器在批次创建后改过目标 → 冲突拒绝绝不覆盖 (Q1 VS Code 场景机械保证); 多批 approve all 按创建序, 后批基线过期 → partial 报告人工; 冲突教训入 ExecutorLessonMemory (staging-conflict:<file> 频率加权)。
- **指令**: /staged [--json] /staged diff <id> /approve <id|all> /reject <id> /cleanup (Known+switch 臂+V2 特判渲染 0ms 本地拦截, /skills 族同款); --json 单行输出供前端 (Q5: 状态文件 data/staged/index.json 也可直读)。
- **验收**: **591 单测绿** (+10 StagedApproval: staging 落盘不占真实地址/恢复/apply 成功/用户编辑冲突拒绝/新建语义/多批顺序+冲突/reject/过期三阶段/--json/损坏容忍); AOT 0 IL 警告; **E2E 三场景真机** (AOT host): /staged+diff 查询 ✓ → 模拟 VS Code 编辑 → /approve ⚠冲突未覆盖 (文件保持 USER-EDITED-IN-VSCODE) ✓ → 恢复基线 → /approve ✓已应用 1 项 (AGENT-PRODUCED-CONTENT 落盘); 批285 (round 512) quick-13 13/13 tok/case 1765。
- 下轮: v0.17.2 窗口&任务感知 (OOB 钦定) + 脚本增强计划 (OOB 钦定)。

## R334 v0.17.0 执行层稳固化 T1-T4 (批284 quick-13 13/13)

- **立项**: 用户钦定 (2 agent 同时写 1 文件族问题 → 工业化 IO 防御) + plan docs/plans/v0.17.0-executor-hardening-plan.md。
- **T1 跨进程锁**: src/agent/execution/FileLocking.cs — FileLock (.lock 文件 FileShare.None=Unix flock LOCK_EX, 持有者崩溃内核自动放锁, 锁文件含 pid); AtomicFileWriter (tmp+Flush(true)+Move overwrite 原子); 删除竞态防护 (释放后校验锁文件仍属自己 pid 才删)。
- **T2 占用者检测**: OccupantDetector — 快路径读锁文件 pid; 主路径 /proc/locks (解析实证 Linux 6.8: "1: FLOCK ADVISORY WRITE <pid> <dev>:<inode> 0 EOF", pid 是含 inode 段前一项, 非固定 index); stale 判定 /proc/<pid> 不存在。
- **T3 教训临时记忆**: ExecutorLessonMemory — 失败→原因→临时记忆, **频率加权增长** (count1 摘要/count≥3 补方案/count≥8 补上下文), 24h 降级 7d 移除 (时钟注入), 手写 JSON 持久化原子写 (踩坑: JsonEncodedText.ToString 带引号致双引号 JSON → 手写 Esc; Save 拼接缺引号 → Esc 包引号)。
- **T4 接入**: TaskCharter.Save → WriteIf (同 Id 状态推进覆盖/异 Id 让位 — KeepExisting 会让 TaskCharterTests 失败: 自身 planning→done 被挡, 教训=自身生命周期推进 ≠ 异主冲突); GuardrailMemory.Save → 加锁 Overwrite; 冲突结构化 + Record 教训 + executor_write/executor_lesson 打点。LockedFileWriter.WriteIf (锁内条件覆盖, 无 TOCTOU)。
- **设计踩坑 (FileShare)**: FileShare.Read 实测同进程第二 Open ReadWrite 仍成功 (不互斥, 测试实证) → 必须 FileShare.None; FileOptions.DeleteOnClose Unix=打开即 unlink → 破坏锁文件可见性。
- 验收: **581 单测绿** (+11 ExecutorHardening: 双锁互斥/stale 接管/活锁不误删/占用者报告/原子写无残留/KeepExisting 让位/教训频率升级衰减/持久化往返/损坏容忍/8线程120行并发追加零丢失); AOT publish 0 IL 警告; 双进程 flock 竞争 smoke (60/60 全成功零交错 — smoke 判定假警报已诊: split 后段天然无分隔符); 批284 (round 511) quick-13 13/13 tok/case 1672。
- 下轮: v0.17.1 离线变更+用户审批 (OOB 钦定, plan 已建 docs/plans/v0.17.1-staged-approval-plan.md)。

## R333 v0.16.4 P10 锚词提取 long-key 零分配 (批283 quick-13 13/13)

- **现状**: ExtractAnchorWords (ContextAssembler.cs L1000) 中文 2/3/4 字全滑窗每位置 3 次 Substring 短串分配 — 压缩热路径 (每超限 snippet 一次, 大片段 ~65K CJK chars → ~200K 分配/片段)。
- **修法**: CJK 全在 BMP (UTF-16 单单元 ≤0xFFFF) → 窗口编码 long key (每 char 16bit 顺序拼, 低位=窗首; 起点必 CJK 使高 16bit 非零、每 len 独立字典 → 键域无歧义) 零分配计数; 仅 count≥2 候选解码 string (AddDecoded 固定 len 正向移位)。
- **语义等价证明**: ExtractAnchorWordsEquivalenceTests 10 测 — 反射调 private 新实现 vs 内联旧 Substring 算法: 6 已知样本 + **40 轮随机混合语料 (CJK/ASCII/标点/emoji/超长词) 全等**。中途设计漏洞自捕: while(k!=0) 解码无法定 len + 低位反序 → 改 3 独立字典分 len。
- 验收: **570 单测绿** (+10); AOT publish 0 错误 0 IL 警告; 批283 (round 510) quick-13 13/13 tok/case 1712 (vs R331 1875 / R332 1889 — 更低, C19 重案方差内; pass-rate 主判据干净)。

## R332 eval per-case isolation hardening (批282 quick-13 13/13)

- **根因**: run_round.py 清理只在轮级 (R81), case N 落盘会话记忆 (data/sessions/cli-*_memory.json, CLI 每进程读+追加写) + RAG index 泄入 case N+1 新子进程 → C14 isolated=None 两次 12/13 flake (rounds 506/506b; R331 A/B: 同 binary standalone 2/2 PASS + OLD 13/13 PASS, 失败仅现整批窗口 = cross-case leakage 时序累积)。
- **修法**: case 循环内每 case 前清 sessions + RAG 落盘 (setup 键仅 charter/guardrails 且 fixture 在 run_case_with_setup 内应用 → 清理先于 setup 安全; repl 型 case 内部多轮共享进程状态不受影响)。
- **教训 (执行层)**: execute_code 内 Popen 起批测会被 cell 300s timeout kill 连坐 (半批 16/16 PASS 无汇总即死) → 长批必须 terminal background=true + notify。
- 验收: 批282 (round 509) quick-13 **13/13** (tok/case 1889 vs R331 1875 同水平; C14 PASS); 508 半批 16/16 (被连坐前)。AOT 无需重发 (eval 层改动)。下轮候选: P10 锚词 Span 化 / RAGConfig 内联 hash 收敛 / dormant 退役 (需裁定)。

## R331 v0.16.3 RAG 落盘裁剪摊销 (P12, 轮507 13/13 验收)

- **背景**: function-map-R326 P12 — RAGConfig.PersistDocument (L231-262) 每 append 后无条件 `File.ReadAllLines` 判 512 行裁剪, 超限 `WriteAllLines(lines[^512..])` → 库过 512 后**每消息整读+整写** (~512 行恒定浪费 O(库大小) 文件 IO); 增长期 1→512 每 append O(n) 读 = O(n²) 累计。每用户消息热路径 (对话库逐轮涨)。
- **改动**: 常量抽取 `RagPersistMaxLines=512`/`RagPruneInterval=64`; `Interlocked` 计数 `_persistAppendsSincePrune`, 仅每 64 次追加整读一次判裁剪, 超限重建保留最新 512 (`lines[^512..]` 语义不变)。文件瞬时上限 512+63 行 (有界松弛), 每次裁剪终态与逐次裁剪内容集一致 (追加+保尾裁剪单调); 文件被外部删除/重建后计数器最多漂 64 次 append, 下次裁剪整读实测自愈。
- **验收**: **560 单测绿** (+3 RagPruneAmortizeTests: 700 文档 → 文件行数 ∈(512,575] 且保最新裁最老 / 新实例重载只恢复幸存者+追加继续正常 / 小库 50 行零裁剪); AOT publish 13.2MB **0 IL 警告** + CLI 冒烟; 批测轮 507 quick-13 **13/13 零回归** (tok/case 1875 超旧健康带 = C19 8523 级重案 + LLM 方差, R329/R330 同判型; 通过率主口径零回归)。
- **C14 整批 flake 调查 (非本改动引入, 留档)**: 轮 506/506b 均 C14 isolated=None FAIL (12/13, tokens≈1000=未 spawn 隔离链); 同代码单跑 C14 ×2 PASS (isolated=True score=2) + 轮 507 整批 C14 PASS + 旧代码 86a4f13 A/B 整批 (506old) 13/13 C14 PASS → 失败集中于 05:00-05:15 窗口, 与代码无关。归因: TopicRelevanceEvaluator 是确定性规则器 (R308), C14 方差来自**输入**: turn1 锚/goal 的 LLM 提取质量 + **跨用例 tendency/画像泄漏** (run_round R81 只轮级清 RAG+会话记忆, case 进程共享 tendency 文件 → 前序 C07/C13 输出随 LLM 方差变化, 泄漏进 C14 锚提取 → 弱锚/无锚路径不隔离; 失败回复实测引用前序用例 "Web API 项目/代码推送" 上下文坐实泄漏)。→ 下轮候选: eval 隔离按 case 清理 tendency/画像状态 (harness 硬化)。
- 收益: 库过 512 后每消息文件 IO 整读+整写 → 每 64 消息一次 (64× 摊还); 增长期读 O(n²)→O(n)。
- 下轮候选: P10 锚词 Span 化 / C14-in-batch 隔离硬化 (eval 按 case 清 tendency) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实命中分布数据) / dormant 退役 (需用户裁定)。

## R330 v0.16.2 工作区召回流式化 + 整轮字节预算 (P4 首段, 批282 13/13)

- **背景**: function-map-R326 §4.1 P4 — ContextAssembler.RecallFromWorkspaceAsync 每文件 `ReadAllTextAsync` 整读 (≤200KB/文件 × ≤300 文件 → 单轮理论最多 ~60MB 文本读入 + `Split('\n')` 全行数组数千短 string 分配/文件), 无整轮读取预算; 文件/编码类意图每装配触发 (recall_workspace 打点监控), 中热。
- **V1 流式化**: 整读+Split → `StreamReader` 逐行 (`FindKeywordLineRankedStreamingAsync`), 峰值内存 = 单行。**语义与字符串版完全一致 — 无前缀截断, 文件尾部命中不丢** (35KB 深处命中单测锚, 前缀否定需真实命中分布数据, 未做, 候选); 单行命中计数抽 `CountKeywordHitsInLine` 双版共享防漂移 (FindKeywordLineRanked 字符串版保留, WorkspaceRelevanceTests 反射锚)。
- **V2 预算化**: 满分档 (5 hits) 命中即停读 (原整读后 break 无 IO 收益); 整轮字节预算 `WorkspaceRecallBytesBudget`=4MB (static 非 readonly — 单测反射注入小预算验证截断路径), 超预算停止扫描剩余文件 — 与 Take(300) 同哲学 (按修改时间降序, 丢最旧文件; R30 已声明"扫描窗口内召回质量"边界); 空文件跳过。
- **验收**: 557 单测绿 (+4 WorkspaceRecallBudgetTests: 文件尾部 ~35KB 关键词命中不丢 / 预算 2KB 截断只留最新文件 / >200KB 大文件跳过 / 多词最佳行 R118 相关分语义); AOT publish 13.2MB **0 IL 警告** + CLI 启动冒烟; 批测 505 quick-13 **13/13 零回归** (tok/case 2004 超旧健康带 = C19 8523/C14 4291/C13 2616 重案 + LLM 方差, 同 R329 判型 — 通过率主口径零回归, hash/bge 路径不受影响)。
- 收益: 工作区召回峰值内存 整文件→单行 (大文件数千行数组分配消除); 单轮读取上限 理论 ~60MB → 4MB 预算窗口。
- 下轮候选: P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实工作区命中分布数据) / dormant 退役 (需用户裁定)。

## R329 v0.16.1 HashEmbeddingProvider 双实现统一 (T-B4 遗留收口, 批281 13/13)

- **背景**: v0.15.3 计划 T-B4 遗留 — 三份 hash 语义并存: vectormemory 384 英文版 (EmbeddingProvider.cs) / llamalocal **256 硬编码版** (EmbeddingRouter.cs, bge 缺失兜底) / RAGConfig 内联 (RecallRateTests 锁定, 不动)。两 class 注释均自称 "R58 语义" 但实现矛盾 (256 vs 384 维度分裂、英文-only vs 中文标点、单桶覆盖 vs 3-seed 摊开)。
- **V1**: vectormemory.HashEmbeddingProvider 升级为统一唯一实现 — RAGConfig.Tokenize 同族分词 (lower + ASCII 标点全切 + ascii↔非ascii 边界切 R44 中英混写 + 中文 2-gram 滑窗 R6) + 3-seed 摊开桶分配, dim 可配默认 **384**; 不做预归一化 (全部调用方 CosineSimilarity 自归一, 与 RAGConfig 内联一致)。
- **V2**: llamalocal.HashEmbeddingProvider (256) **删除**; EmbeddingRouter fallback → vectormemory 统一版 (384)。grep 全仓无残留。
- **验收**: 553 单测绿 (+5: 维度 384/中文多桶/R44 混写召回/R6 无空格召回/EmbeddingRouter fallback 指向统一版); AOT publish 13.2MB **0 IL 警告** + 冒烟; 批测 504 quick-13 **13/13 零回归** (tok/case 1877 超旧健康带系 C19 重案 8877 + LLM 方差, 逐案对比 C03 -1076/C13 +1199/C19 +1563, hash 路径批测不参与, 非本改动引入; 批279 1687 亦在旧带外 R322 已知)。
- 收益: 降级/AOT 形态 RAG 与记忆整合向量空间统一 (384), 中文召回从整句 1 桶升级为 2-gram + 边界切 (R6/R44 语义覆盖)。
- 下轮候选: P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需用户裁定)。

## R328 v0.16.0 skills 引擎完整落地 (批280 37/37 验收)

- **CLI 外挂 skills** (用户钦定 v0.16.0-a): `--skills-dir <目录>`(可多次)/`--skills-blacklist <id或目录名>`(可多次)/`--skills-file <单SKILL.md>`(可多次) → env 钩子传 DI → ServiceCollectionExtensions 合并注册; 外挂同 SkillId 覆盖内置 (Register 字典后写胜); RemoveById 精确 id+包目录名双匹配。E2E: 外挂 my-ext-skill 进注册表 (7 个激活)。
- **运行时动态过滤** (v0.16.0-b): SkillRegistry.SetActiveWhitelist/Blacklist (volatile HashSet, All getter 应用, null=清除) — 循环任务内动态指定可匹配范围。
- **/skills 指令族** (v0.16.0-c): /skills 查询当前激活 (id/版本/类型/触发词)、/skills-only /skills-exclude 动态过滤 — Known+TryRoute switch 三臂+V2 特判渲染 (Dispatcher.Registry 只读暴露)。**根因教训: Known 集合加了但 switch 臂没加 → 落 _ => NotCommand 送 LLM (模型幻觉能力表); SkillsCommandRouteTests 测试先行逮住**。
- **skills 格式统一**: 6 包全部规范 frontmatter (name/description/version/type/keywords; image-gen 补缺失→knowledge_hint; normative 显式化)。
- **critic-rules 语言无关化 2.0.0**: R01-R08 按语义定义 (堆分配/串拼接/async void/阻塞/吞异常/判空/浮点比较/资源释放) + C#/Python/Go/Rust/Java 映射; config 同步去 domains:[csharp]。
- 验收: **548 单测绿** (+SkillsCommandRouteTests 2); 批280 全量 37/37 (mass 503, tok/case 2075 = 全量口径含 C19/C16 重案+诱饵族, 非回归); AOT publish 0 错误。撞号险情 1 次 (误取 502 与批279 冲突, R257 协议 30s 内 kill 换 503, 旧文件零损失)。
- 下轮候选: R-3 HashEmbeddingProvider 双实现统一 / P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / dormant 退役决策 (需用户裁定)。

## v0.13.x (2026-09-08~09) — 底座能力与收敛环 (已落地, R205-R288)

### 主题 (用户钦定): 渐进式探索 / 思考链收敛 / 兜底粘性路由 / 格式修复收敛环 / 底座能力长期观察

### ✅ 完成记录 (真实执行)

**v0.14.0 输出侧经验闭环 + v0.15.1 任务路由 (R318-R322, 2026-09-09)**
- OutputCritic (R318): 8 条 C# 反模式静态规则, 14 测; plan 三版演进 (孤立设计→用户纠正"回顾既有牵引体系"→master-plan S/M/D 盘点+第四环定位)
- SelfCritic (R319, 用户钦定方向): LLM 自审=人类经验检索 (常见反模式分布内可靠); 三失效模式 (过度批评/幻觉批评/分布外) 对策=逐字子串锚+机制解释强制+Anchor 过滤; 单源自评绝不直接进生成上下文
- FixMemory (R319): 修法记忆 (反模式→修法), 来源秩 human_review > metric_delta > llm_self_confirmed; R0071 误信全仓清零 (用户纠正: 非本项目编号)
- CriticPipeline (T2c): 静态=确认态 / LLM 交叉=去重 / LLM 单源=观察态不入上下文
- T2d 接线: DataSourceType.FixMemory + ContextAssembler 分支 + K1 全隔离剔除 (R302 对齐); 装配接线 3 次插错教训=多块编辑用 git diff 不做行号算术
- TaskCharter (R322, v0.15.1-a): 章程 schema + 任务进行中新输入三态路由 (supplement→pending / pivot→归档 failed / isolate→既有链); E2E 三态实证 + 归档快照修正 (Archive 先 Save 终态再 Move)
- 数据: 批263-265 全绿 (12/12 quick-12); 538 单测

**v0.13.3 牵引收口与重构事故自捕 (R309-R313, 2026-09-09)**
- 缺陷 72 修复 (R309): executive 直达补 intent 打点 (C04/C06 intent=general 复现; llm_calls=0 保留=executive 本质无 LLM); init 键教训第 3 次 (R142/R151/R309) — topic_* 键加错 init dict, 批254 KeyError 杀批
- 牵引阈值 env 化 (R309): AGENTFRAMEWORK_TOPIC_STEER_THRESHOLD (默认 2)
- explore 执行方式修复 (R310): AOT apphost framework-dependent 无 DOTNET_ROOT 秒退假跑 → dotnet dll 对齐 run_round; 24 案真跑 A 0.167/B 0.722 (+56pt 历史最高); B 轮 3 viol 定性=must_not_contain 与引用来源的判定张力
- 否定围栏双向化 (R311): 前 40ch + 后 20ch (后置否定 "并非光合作用" 兜住); 3 形态离线验证; 批256 负样本零回归
- 无锚轮词面 verdict (R312): R308b 删词面退路致无锚会话牵引失效 → else 分支纯词面模式; 但**重构事故**: 有锚隔离执行链误删 → 批257 C14 首败 (isolated=None) 实锤 → R313 恢复
- 衔接副词精修 (R313): "再讲 X" 单字"再"误判指代 → 裸衔接词 + 无复合指代在场 + 词面偏离成立 → veto 不适用; 💡 提示链恢复 (SteerHint ×2)
- 欠账补齐 (用户点名): 批 188-217/218-247 两段归档 (R312), archive-first-then-retire 制度
- 数据: 批255 11/11 1228/case; 批256 11/11 1161/case; 批258 11/11 1003/case (C14 复绿)

**v0.13.3 合并判定与复查收口 (R307-R308, 2026-09-09)**
- L1 轻牵引 (R307): 连续偏题 ≥2 轮 → 回复尾追加衔接提示 (答案本体零改动); 追加位置必须在区段路由**之后** (ProcessAsync 会重写 Content — E2E 实证)
- TopicRelevanceEvaluator (R308): 隔离+牵引合并判定 API — 一份 verdict 三路消费 (Isolate→subagent / SteerHint→牵引 / Normal); 分级 veto (指代词绝对 / 短询问在实体非零重叠时)
- 复查三轮 (用户钦定): ①首查 4 缺口 (隔离点直调 Check / steering 独立打点 / verdict 双算 / 旧注释) ②二查 3 缺口 (run_round 零消费 topic_relevance / K1 双开关语义 / no-anchor 观测盲区) ③三查围栏双脚本同源 — explore_eval 窗口 20→40ch + 词表补 "不能" (TC-F06 离线双向 4/4) + suspect 降级语义统一
- **缺陷 72**: skill executive 直达路径 (L481 early-return) 绕过 LLM 后全部打点 — C04/C06 llm_calls=0 结构性根因 (批244 起即如此, 此前误标瞬态)
- 数据: 批250 11/11 1172/case; 批253 11/11 1061/case; 499 单测; 探索增益口径澄清 (R288 可达 11 案 +18pt / R289 全 24 案 +39pt, README 用后者)

**v0.13.3 宿主执行与真机 E2E (R272-R288, 2026-09-09)**
- 思考链宿主执行全线打通 (R286): HostExploreExecutor (URL GET digest/页内链接发现≤5/目录文件路径穿越防护) + V2 RunThinkChainAsync (播种→4s/4步→首败即停→回注); 真机 think_chain {seeded:1, steps:1, ms:46}
- **探索 KPI 正信号** (R288/R289): 可达 URL 24 案 A/B — hit **0.278→0.667 (+39pt) ↑7 ↓0 零回归**; wall B≤A (成本不可见); explore_eval 独立跑测程序 + 本地夹具 8 页 + A/B 开关 AGENTFRAMEWORK_EXPLORE
- LinkRegistry 激活链 (R276/R282): 三信号 (锚定/稀缺出链/路径递进) ≥3 激活+父链保护; 真机 link_activation {urls:5, activated:5}
- think-memory 持久化 (R283): Save/Load (STJ source-gen 流式零反射) — 新进程 recall hit top_sim 0.9701 (data/think-memory.json)
- 微步骤宿主链 B2 (R274): gate=IsolatedMicro → 微问询 → 回注 ≤200tok/条; E2E 2860ms failures=0
- 压缩失败防护 D1-D4 (R262-R265): 异常隔离/数字+URL 哨兵 (链接文档 URL 键全档 100%)/降级链/熔断器; 多轮 3 场景 (A=35/B=12/C=22 压缩事件 sentinel 全 0)
- 多轮 driver 场景参数化 (R278): MT_SCENARIO=A/B/C; 10 轮 repl × 压缩遥测 17-35 事件全健康
- 缺陷台账新增: 跑测程序回复区误报 (R273 修: 回复区提取+否定围栏) / build 单项目不刷 host bin 依赖 (R274 教训) / probe stdout 管道满冻结 agenthost

**v0.13.0**
- 渐进式探索: ExplorationConfig (每上下文区/文本/URL/目录最大探索步 + 全局预算 + URL 深度) + ExplorationPlanner (优先级队列; 用户例: 上下文内 URL > 上下文外目录) — 7 单测
- 思考链 T3: ComplexityGate + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先历史高置信链接, 引用后 +0.05 置信, 负样本降权, 30 天衰减) + ThinkChainSession — 12 单测
- RAG 数据文件用户指定: CLI `-rag <path>` / 任务内 `/rag` / env 三入口 (真机三态验证)
- Baseline 换血 (用户钦定): L0-L5 分层; XL 大上下文族真机验证 (XL-01 实测 7010 tok, 回复含全部 ground truth; XL-04 10750 tok); ContextBudgetGate (WARN 6000/HARD 9000, 防抖首次跨越放行修复 — python 复现抓 bug) — 6 单测

**v0.13.1**
- 兜底粘性路由: FallbackConfig (config 开关 + cost_quality 性价比序 + 逐个兜底 + 回复校验, MinReplyChars=2 由 Router 测试实证) + Router 逐个兜底链 (fallback_attempt/fallback_verify_fail 打点) + StickyRouteMemory (三门判定: 相似+意图+实体指纹; 最近成功优先 0.01 容差; TTL 72h) — 11 单测

**v0.13.2**
- 格式修复收敛环: IFormatRepairPlugin + JsonRepairPlugin (栈感知括号修复; 用户破损 JSON 实例回放通过) + FormatRepairLoop (①块内检测→②查找→③校验→④本地修复→⑤LLM 循环; max_llm_rounds 可计数; 技能-校验矩阵硬规则) — 13 单测

**v0.13.3**
- 底座能力长期观察 (用户钦定, 入 master-plan §0-2): 压缩 audit (`--compression-audit`, 104 篇多样态 ground-truth × 4 档 × 3 级别)
- A3 关键句保护修复: TakeSentences 评分保留因果/指令句 — SummarySentences 因果/指令保留 0-20% → 单样式 100% / 多样态 99% (keys) / 85% (指令, 无标点样式待修)
- 429 感知调度: 限流跳过同模型重试直切备 (省 ~1000 tok/次重发)
- token-breakdown 每批观测行 (prompt/history/completion)
- 微步骤隔离设计 A6 (阈值门控, 更正2: 未达阈值走常规; 触发率基线 0%)

**缺陷修复 (本段)**: 真缺陷 65 (重试/切备成功路径 llm_call 打点缺失→429 后 token 全丢, 批187 假性 KPI_BREACH) / 66 (文本请求备选落视觉模型成本倒挂) / 67 (Text 能力硬过滤, cogview 误入文本备选) / 68 (C17 断言脆性 → neg_context_markers 推测围栏, 双向回放验证)

### 📊 基线
- 测试: **468/468 全绿** (404 → 468, 含探索 7/思考链 12/兜底粘性 11/格式修复 13/预算门 6/视觉族 3)
- AOT: publish 0 IL 警 (多次重发布); 批测: 批 174-217 带内 (600-1250 tok/case), full-23 23/23
- 文档: CLI 指令说明三表重构 (会话指令/本地命令/启动参数); docs/ 全量审计 (6 文档归档, 断链 0)

---

## v0.12.0 (2026-09-08) — 视觉理解 / 渲染插件 / 收敛环 (已验收)

### ✅ 完成记录 (真实执行)
- **视觉理解链**: CLI `-img` → Message.ImageAttachments → data URL base64 → glm-5.3-flash v4 端点; text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64); OpenAIMultimodalMessage 双形态 DTO (string|parts[], AOT-safe 手写 converter)
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin 契约 + SkiaSharpRenderPlugin (默认 PNG, 边缘选项 `-p:DisableSkiaRenderer=true` 停编) + SvgTextRenderPlugin (零依赖兜底) + ImageRenderPluginRegistry (HasRenderer=false → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义, 栈感知)
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → FAIL 重生成 → PASS (真机一轮 PASS: DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定 R210 弃用)
- **验收**: T-V01~04 视觉用例族 full-23 23/23 (含负样本诱饵识破: 模型拒绝"右下角苹果"假预设); 四问真机复证; 基线 docs/archive/reports-archived/v012-acceptance-baseline.md

### 📊 基线
- 测试: 415+ 绿 (视觉 DTO 5 + 渲染器 3 + 插件 4); AOT 0 IL 警

---

## v0.11.0 (2026-09-06) — 统一命令协议 + 三传输 + Skill 脚本执行

### ✅ 已完成 (真实执行)
- **agent.io 统一命令协议**: `AgentCommand` 信封 (@cmd name key=value 行协议, 百分号转义手写编解码 — 零依赖 AOT 安全) + `AgentCommandWriter/Reader`; AgentReportReaderBase 加 Command 事件分类
- **三种传输**: Console.IO / 共享内存 (文件-backed mmap 环形区, 背压可见) / TCP Socket (跨机)
- **LogRouter 双通道**: thinking/输出指令同时镜像 IChatboxSink + @cmd
- **SkillScriptRunner**: SKILL.md 包 scripts/ 真进程调度 (python/bash/node PATH 探测; cwd=包目录沙箱; 环境变量白名单; 超时杀进程树; 脚本 @cmd → AgentCommandWriter 转发)
- **SkillDispatcher 接线**: executive 无显式 entry → 包脚本自动执行
- **性能修复 (sync-over-async 清剿)**: ModelQueueRouter.OnTransientFailure → async 链; TriggerMatcher.MatchAsync; ContextGradientCompressor.CompressCoreAsync
- **模型目录 6 → 18**: +Anthropic/Google/xAI/Moonshot/Qwen/DeepSeek v3.2/OpenAI/GLM-4.5 — 全部公开牌价, /model verify 可校验

### 📊 基线
- 测试: **351/351 全绿** (+10: 命令协议 6 + 脚本执行 4)
- AOT: publish 0 IL 警; /model list 18 模型真机确认

---

## v0.10.0 (2026-09-06) — Yamlify 换库 + Token 统计/余额联动 + Skill 语义

### ✅ 完成记录 (全部真实执行)
1. **YAML 解析换 Yamlify 1.8.0** (MiniYaml 重写为门面): AOT 零 IL 警; `TryGetTopLevel` 修复顶层列表键真 bug; API 签名不变 → 5 消费者零改动
2. **Token 使用统计 + 余额联动** (TokenUsageService): 真实 API 同步 → 本地累计 → 阈值再同步; 余额不足切模 + flags 提示; `/token stats` 全 JSON
3. **Skill P3 语义匹配接 bge** (TriggerMatcher): 词面全未命中 → bge 余弦 ≥0.45 疑似判定; 失败静默回退词面
4. **官方端点可配置代理** + **统一输出收口** (host 8 处 Console → IOutputSink; 库内零 Console 直写) + **/forecast 指令** + **/model list 序号选择** + **LocalLlamaCaller DI 修复** + **版本号统一 15 csproj → 0.10.0**

### 📊 基线
- 测试: **341/341 全绿**; NativeAOT publish 0 IL 警 (agenthost 12MB ELF); AOT 冒烟 4 项通过; GitHub 推送 387bfb1

---

## 历史遗留 (v7.x — v0.x 前身版本号体系)

> 以下为 v0.x 统一编号前的历史记录, 原文保留; 详情见 git log 与 docs/changelogs/CHANGELOG-v7.14.md。

### v7.15 (2026-09-05) — 十节点全落地
十节点: ①Skill 调度 P1 ②模型队列与意图选模 ③日志四通道 ④上下文梯度压缩 ⑤影子计划 ⑥问询打通 ⑦会话恢复 ⑧公开配置读写 ⑨agent.io 协议库 ⑩能力插件接口。需求四项: ①官方通道混合调度 ②agent.io ③会话中断恢复 ④公开配置读写。基线: 276→325 测试全绿 / AOT 0 IL 警 / 双冒烟通过。

### v7.14 (2026-09-05)
EvidenceGate→ClarificationBatch 接入 V2 主链 / vulkan setenv 双写 / SessionMemory 滚动 / AgentProfile 动态学习 / CapabilityScanner 重构 / 目标锚免压缩 / 面板全 JSON。基线 218/218。

### R380 承接: BGE 训练闭环打开后的首个诚实结论 (待核实 1 项)
- **闭环通了**: 模型路径候选回退 + 矩阵形状归一后, `train_adapter.py` 96s 内跑完并把 `docs/reports/bge/versions/v1.md` 写出 (此前 3 次全在 900s 死等后失败)。
- **诚实边界**: 判定 `rolled_back` —— T1 适配器 **未过 G1/G2**(r@1 0.2667 vs 基线 0.3083), 闸门正确拒绝采用劣化模型 (负样本诚实原则生效)。
- **已定位并修复 (R380 收口)**: ridge 配置 r@1=0.0/median_rank=999 的根因是**两层真缺陷叠加** —— ① **拟合空间 ≠ 应用空间**(拟合用未 λ 缩放的 `_base`, 应用时 W 乘在 `_base/λ^α` 上); ② **转置错**: `(QᵀQ+λI)⁻¹QᵀP` 是**列定向**解(= Wᵗ), 旧代码直接 `matvec(W,·)` 当 W 用。
  - 统一出口转置 + 同空间拟合后真机: **median_rank 999 → 23 / r@1 0.0083 → 0.1750 / r@10 0.0583 → 0.4250**。
  - 机检 `eval/bge/test_ridge_space.py` (同空间 cos **1.0000** 精确复原 + 异空间**反向控制**必须显著变差) → 4/4。
  - **结论订正**: ridge 在修正实现下仍不及基线 (0.1750 < 0.3083, G1/G2 未过 → `rolled_back`), 故"ridge 无收益"这回**有依据**; 此前结论建立在错误实现上, 不成立。

### R383 (2026-09-13) — D4b 出站扣减 + T4 真跑闸门决策 + D7 运行时依赖等待
- **D4b 出站扣减** (修 R382 §9.5-2 的重复计算): 已判**本地执行**的子请求**不再发给模型** —— 路由是"谁来做", 不是"记账"。三层确定性判据 (节点级 R2c / 片段级 `RequestAblation` / 计划级闸门"仍有远程节点才扣"), 保守方向"定位失败/多处/剩余<25%/全本地 ⇒ 一律不扣"; 扣减掉的子请求由框架自渲染进答复 (`PlanLocalAnswer`, 失败也如实说明)。**真机**: 远程节点 **2→1**、出站 **117→100 字符**、答复里的字数由模型自算 **118(错)** 改为框架算 **117(对)**、tokens 38,275→30,501 (指示性)。机检 `PlanAblationTests` **24 例**。
- **T4 决策**: `AGENTFRAMEWORK_PY_RUN` **空值 ⇒ 默认跟随"是否已装固定解释器"** (只有 PATH 兜底时保持不跑 —— 不可复现的通过比不通过更危险); 解析顺序单一事实源 (`explicit → 仓库固定记录 → uv 托管 → PATH`), **解释器来源进结果与遥测**; `scripts/fetch-py-tool.sh` 固定 CPython 3.12.14; 闸门只对 `.py` 开放。**真机**: `script_run{ran:true, exit:0, ms:32, interp=…cpython-3.12.14…}`。机检 `PythonInterpreterResolverTests` **9 例**。
- **D7 运行时依赖等待** (用户 OOB 新增测试点): A 跑到中途要用 B 的产出, 而 B 未产出/在等用户 ⇒ **A 等待, B 产出后才继续** (不消费输入/不伪造/不静默)。确定性契约 `$node:<id>`、`$dep:<id>`、`<id>的产出`; **等待不占并发额度** (延迟队列, 额度=1 也不死锁); **有界等待**超限如实失败 (不采用迟到产出); **成环在记账时即拒**; 生产节点在等用户 ⇒ `PausedForDependency`; 提前终止时等待节点明确落终态 (不留悬空 Waiting); 前端可见 `plan.node{state:Waiting, wait_for, wait_reason}` + `plan_wait` + KPI `WaitNodes/WaitUs`。机检 `PlanRuntimeWaitTests` **11 例**。
  - **诚实边界**: **跨轮唤醒 (D7b) 未实现** —— 检查点 `SaveCheckpoint` 只写不读 (无 `LoadCheckpoint`/续跑入口), 用户回复后不会自动续跑; **自然语言引用不认** ⇒ 真实任务要出触发点必须先做契约**前置注入** (D7c)。
- 基线: **949/949** (891 + PlanLocalFirst 14 + PlanAblation 24 + Resolver 9 + RuntimeWait 11); AOT 发布校验按登记口径只在发布 tag 执行。

### R384 (2026-09-13) — D7b 跨轮唤醒（装载入口 + 续跑消费方）
- **补齐结构缺口**（R383 诚实边界 1）: 此前检查点 **只写不读** —— 生产节点在等用户时计划停在 `PausedForDependency`, 用户把答案发回来**没有任何消费方**（被当成全新任务重拆, 永远等不到续跑）。本轮加 `PlanResumeService`：**Capture**(蓝图+运行态+真产出+卡住节点+问题) → **Load**(拆解**之前**拦截, 从检查点重建 plan/run) → **ApplyReply**(答复落到确定参数槽) → `PlanRunner.RunAsync(seedRun)` 从上一轮运行态继续, 已 Completed 节点**不重跑**、等待节点被**真产出**唤醒。
- **四条硬纪律（机检逐条钉）**: ①不重拆（拦截点在意图拆解前）②不伪造（生产者已 Completed 而快照缺其产出 ⇒ 装载入口**直接拒绝**, 不接受空着喂/重跑生产者）③不猜（无参数名/多条目/不在选项内 ⇒ 拒绝落地并作废该检查点, 如实告知）④不留悬空（跑完清检查点; 再次暂停重新捕获; 等待台账跨轮闭合, `WaitUs` 含用户思考时间）。
- **两个实现要点**: `ClarificationsSettled`（答复落地后证据门槛**不再重复问同一句**; 其它低置信节点仍正常提问）; 续跑批次过滤已 Completed 节点（`order` 保持完整以保生产者查找）。
- **跨进程真机证据**（两个独立 dotnet 进程只共享检查点文件）: A(write) `state=PausedForDependency, awaiting=b, order=[]`; B(resume) `state=Finished, order=[b,a], a_input=out-b, slot_value=数据是 42, wait_ms=9`。落盘键位 `PlanJson(1682 字符)/RunJson(625)/NodeOutputs/SourceText/AwaitingNodeId=b/PendingQuestion=要处理哪个文件?`。
- **产品链路真机 E2E**: 用产品序列化器在真机数据目录预置可续跑检查点 → `agenthost --session-id cli-r384probe -q "数据是 42"` → `plan_resume{resumed:true, state:Finished, nodes:2, waits:1, slot:target}`、两个节点全本地 `Completed` (`tokens:0`)、**整轮遥测无 `llm_call`（零 LLM 调用/零 token）**、答复渲染为 `🔄 续跑计划 r384-probe …`、跑完检查点由产品自己清掉。附带产品改动 `--session-id <id>`（原会话 Id 每进程随机 ⇒ 跨进程可复现性不成立）。
- **诚实边界**: D7c 契约前置注入**未做且查明落点不存在** —— 当前**没有逐节点远程生成**（一次远程生成覆盖整段计划, 节点文本由确定性拆解产生, 无"节点级提示词"注入面）; 要落 D7c 须先决策"拆成逐节点生成"还是"把契约塞进同一次生成的指令区"（后者需计划先于出站请求成立, 可进静态前缀缓存）。续跑入口**只认"等用户答复"**（纯等待/崩溃中断不自动续跑; 等审批故意不捕获, 否则会吞审批消息）; 多条目澄清需"逐项答复协议"; 答复落点语义与主链 `AnswerSink`（无槽时挂节点文本）**不一致**; `WaitUs` 跨进程锚点不同 ⇒ 跨进程等待时长只作参考。
- 机检: `PlanResumeTests` **18 例**（6 正向 + 8 负向 + 2 跨进程探针 + 1 审批负向 + 1 产品链路探针）; 基线 **967/967**（949 + 18 新增/探针）。

### R388 (2026-09-13) — 形式化内核三缺口全修 + DCR 口径修正 + z3 独立审计器

- **内核完备性三缺口全修（自检 14/14）**: ① **整数 gcd 必要条件**（显式等式 `Σaᵢxᵢ=b` 且 `gcd(aᵢ)∤b` ⇒ `Sat.Unsat`；必要条件 ⇒ **只可能新增 Unsat，无假 Unsat**）；② 反例搜索窗口由硬编码 `±65536` **参数化**（窗野外可取点、外框无界 ⇒ Unknown）；③ 等式代入由"出现次数最少"**单点启发式**改为**对每个 |系数|=1 的候选主元都代入**（旧启发式挑到 `b` 致目标变量留在策略值上 ⇒ c052–c054 永取不到反例）。修后 c018/c023/c024（传递）、c044/c052–c055（域小）、c066/c074/c077/c079/c081（整数）**全部转决**，13 条不一致 → **0 条**。
- **真装配复跑（L3，零 LLM 调用）**: `agent --formal-eval eval/dcr/dcr_cases.jsonl` ⇒ 145 行 / `gate_enabled=True` / exit 0；**DCR（弃权计合规）= 145/145 = 100.00%** · 保守口径 101/145 = **69.66%** · **可决断集覆盖率 101/101 = 100%** · 决断条目一致率 100% · **主动误判 0**。R387 旧值 91.03% / 60.69%。
- **口径修正（诚实，旧结论作废）**: 原自定"覆盖率 ≥70%"**数学不可达** —— 19 条 `out_of_fragment` + 25 条 `malformed` 共 **44 条设计上就不该决断** ⇒ 上限 101/145 = 69.66% ⇒ 这是**口径设定错误**，不是能力不足 ⇒ 已改**可决断集覆盖率**（分母 = 可决断集）。
- **新增第四条验证腿（独立审计器）**: `eval/dcr/audit_decisions.py` **不 import 内核任何代码**，用 z3 逐条复核装配裁决 —— `Refuted` 反例必须真满足 `premise ∧ ¬goal`、`Proved` 必须真 unsat；实测 **30/30 反例为真 · 33/33 真 unsat · 0 假（`AUDIT_RESULT=SOUND`）**。"反例不是编的、证明不是假的"从此**可机检复现**（换独立实现对账铁律再落一条）。
- **内核层 vs 装配层 19 条差异 = 层职责**（18 条 absent 的 `NoFormal` 语义 + 1 条 goal-only 的契约结构完整性）⇒ **不是判定错误**，装配层才是契约语义的裁决。
- **诚实边界**: **T1–T4（FAVA 的 DCR 公式/分母/弃权处置/aggregate 合并）仍不可得** ⇒ **"达到 90.5%±5pp"仍不能单口径断言**（100% 与 69.66% 分落区间上/下，**达标与否完全取决于弃权是否计合规**）；**【R397 更新】T1–T4 已解(FAVA 正文取证) ⇒ 单一口径定稿 = 145/145 = 100.00%；但口径敏感度实测 30.34pp，且 90.5% 是 801 例 aggregate(含降层损失)、与本仓 145 例不可比 ⇒ 该断言仍不成立；瓶颈已从「口径未知」转为「题集饱和(无区分度)」。**当前题集已**饱和**（100% 无区分度）⇒ 下轮须加硬用例（长轨迹 / 语义降层类）。
- 机检: 全量 **1019/1019**（含 kernel 共享源）；内核自检 `check --selftest` **14/14**；`XCHECK{agree=15, int_gap=0, unsound=0}`。

### R388b (2026-09-13) — agent.rover Transformer 前向推理真机对账（焦点①）

- **交付**: `src/agent.rover/infer/{ModelConfig(152),RopeTable(73),KvCache(100),ForwardPass(303)}.cs` + `Cli/ForwardCli.cs`(173)（新增；未改 csproj、未加 NuGet、零反射、输出走 `TextWriter`）。
- **Phase 1 数学自证（tiny f32，同权重两侧各算）**: GQA(4/2)+untied 与 MHA(4/4)+tied 两个 tiny ⇒ logits `max_abs_diff` **7.27e-06 / 7.63e-06**（判据 <1e-4）· top-5 id **全同** · **逐层逐 token** hidden 对账最差 5.91e-05（相对 ≈1.3e-06，纯 f32 归约次序）。
- **Phase 2 真 7B（DeepSeek-Prover-V2-7B GGUF-Q4_K_M，4.22 GB）**: 单 token **top-1 = 185**、耗时 16.7–19.4 s、**峰值 RSS 374.7 MiB**（numpy 独立参考 **1.98 GiB**，`Swaps: 0` 侥幸通过）；4 token KV cache `kv_len` 1→2→3→4、**top-1 = 13、top-5 = [13,16,17,15,18] 与 numpy 完全一致**、logits `max_abs_diff 6.10e-05`。
- **"没有 7B 张量被全量物化"有账**: `streamed 4023.0 MiB / file 4028 MiB → ratio 0.999`（单 token 把整份权重流式读一遍）、常驻仅 **976 KiB**（61 张 norm）；numpy 参考物化整张 ffn ⇒ 1.98 GiB。
- **主线程独立复核（不采信子代理自报）**: 重跑 tiny + 真 7B 单 token + numpy 参考 ⇒ 逐位复现（`7.27176666e-06`、`top-1=185`、`2.174377744e-04`、top-5 全同）。
- **诚实边界**: 本模型实测**非 GQA**（`n_head_kv = n_head = 32`）、**无 RoPE scaling** ⇒ 两分支只由 tiny 覆盖；**未实现采样/生成循环**（无 temperature/top-p/EOS）；**未做性能优化**（22.2 s/token 受"每 token 重读 15.1 GiB 权重"限制）；单 token logits 绝对差 **2.17e-04 > 1e-4**（值域 44.7–64.5 ⇒ 相对 3.4e-06；top-1 判定裕度为误差的 **645×**，argmax 不在可翻转临界）。

### R389 (2026-09-13) — agent.rover Vulkan 真机落地 + SPIR-V 常量表权威机检（焦点① GPU 路径）

- **旧假设被探针证伪（诚实修正）**: 此前计划书写"本机无 GPU ⇒ Vulkan 只能编译 + 真调 `vkEnumeratePhysicalDevices` 得 0 设备"。`vulkaninfo --summary` 实测 **GPU0 = llvmpipe (LLVM 20.1.2)**（lavapipe 软件 Vulkan ICD 已装）⇒ **Vulkan 路径可真跑 dispatch 并对账**；本轮据此把 GPU 路径从"仅编译"升级为"**真机跑通 + 数值对账**"，并回改 exp10 计划的 C5/GPU/A6 条目（不留旧结论）。
- **交付（全部自研，零 shell / 零反射 / 无 glslang·glslc 环境）**: `Gpu/VulkanBackend.cs`(419 行, instance→物理设备→队列→设备内存→缓冲上传/回读→描述符集→计算管线→dispatch) + `Gpu/Spirv/{Spv.cs(指令级汇编器), Kernels.cs(四内核), SpirvValidator.cs(**独立**结构校验器), SpvDisassembler.cs(**独立**反汇编器, 不入执行路径)}` + `Cli/VulkanCli.cs`(`vulkan` 子命令 / `--spirv-only` / `--spv-dump` / `--show` / `--elements` / `--repeat` / 5 组 `NegativeControl`)。运行库 = `Silk.NET.Vulkan 2.23.0`（与 Silk.NET 同源, 非自造 P/Invoke; API 形状先由一次性反射探针 `/tmp/vkprobe` 定死再写静态代码, 探针不入产品）。
- **真机结果（全绿）**: 三内核数值对账 `fma_vec max_abs_diff=0` / `silu_mul 2.98e-08 < 1e-5` / `scale_inplace max_abs_diff=0`；机制探针 `const_b1_hits=4/4`、`dyn_b2_hits=16/16`、`dync_b3_hits=16/16`、`index_value=8 ∈[0,16)`；`done{kernels=3 pass=3 fail=0 spirv_valid=3 neg=5/5}`；build **0 Warning / 0 Error**。
- **共修 4 处真 bug（前 3 处由独立件抓出, 第 4 处只能由外部权威抓出）**: ① 汇编器 `ExecMode` 丢 mode 字面量 ⇒ 非法 SPIR-V；② 结构校验器 bound 读错 word（`words[4]`→`words[3]`）；③ `AccessChain` 缺 struct 成员索引 0（结构合法、语义错）；④ **自写 opcode 常量表两处错值** —— `OpUGreaterThanEqual = 179`（规范 **174**, 179 实为 `OpSLessThanEqual`）、`OpConvertUToF = 111`（规范 **112**, 111 实为 `OpConvertSToF`）⇒ 守卫 `I >= n → return` 编译成了带符号/浮点比较 ⇒ 条件失效 ⇒ 全部 256 个调用都跑 body ⇒ 动态索引写落 0..255 越界不可见（表现为"dispatch 成功但动态索引写不落地"）。
- **本条最重要的方法论升级（与既有「跨实现交叉对账」铁律同源, 但更狠）**: ④ 号 bug **汇编器、结构校验器、反汇编器共用同一张手写常量表** ⇒ 三者会**互相印证同一个错误**（校验器报 valid、反汇编"逐字正确"）—— 自证链**在原理上看不见**它。只有引入**外部权威 oracle** 才抓到: Khronos 官方 `spirv.core.grammar.json` + `extinst.glsl.std.450.grammar.json`（已钉进 `Gpu/Spirv/registry/`, 附来源 URL + sha256）。**封死措施**: 新增 `SpvRegistryAudit.cs`（零反射 JsonDocument 审计器）+ 机检 `SpvRegistryAuditTests` ⇒ **100 条常量 / 0 不符 / 0 无法核对**, 且带 **4 组负向控制**（改错 opcode / 改错枚举 / 改错 GLSL.std.450 号 / 注入表外常量各一例必须红）—— 审计器自身"没测到"一律进 `Unverified` 而非静默放过（"未验证 ≠ 已验证"）。
- **诊断纪律（可复用）**: "dispatch 成功 ≠ 数值正确" ⇒ 先加数值转储, 再把失效点**逐机制二分**（ArrayLength / 常量索引 / 动态索引 / 常量值+动态索引 / 缓冲绑定位置）；"结构合法但数值错"必须用**独立反汇编器取真值**（据此**证伪**"'SPIR-V 层绑定/装饰错位'整类猜测", 真问题是诊断夹具自身缓冲顺序错位）；夹具缓冲序必须与内核变量声明序**逐位对齐**, 否则错位会伪装成"设备写未落地"。
- **诚实边界**: GPU0 是 **lavapipe 软件实现**, `device_ms`/`elem_per_ms` 只作正确性证据、**不代表真实 GPU 性能**；**CUDA 路径未实现**（本机无 NVIDIA 设备）；Silk.NET 的 Vulkan API 形状由一次性反射探针确定（探针在 `/tmp`, 未入产品）；`/usr/share/vulkan/explicit_layer.d/` 无 validation layer ⇒ 结构校验靠自研校验器 + 5 组负控背书（非 khronos 官方校验层背书）。
- 机检: `SpvRegistryAuditTests` **6/6**（含 4 组负向控制）；全量测试 `1025/1025`（1019 + 6 新增）；`vulkan` 子命令 exit 0。

### R390 (2026-09-13) — agent.rover 驻留/回收接前向：热集常驻 + LRU 主动驱逐真触发（焦点① 剩余件）

- **本条要修的靶点（用户口径 C3/C4 的空白面）**: 此前驻留账**恒 `evicts=0`** —— 即"只常驻活性高的张量 + 不再使用的张量主动从内存释放"里的**驱逐/回收路径从未被走到**，且 `TensorResidency` **未接进前向**（前向完全不走驻留管理）。
- **交付**: `Infer/ForwardPass.cs`（cts 增 `pins` / `reclaimPerToken` 两参；每 token 末 `ReclaimAll()`；暴露 `ResidentCount`）+ `Cli/ForwardCli.cs`（`--budget-mb|--budget-kb|--budget-bytes` / `--no-pin` / `--reclaim-per-token` + `residency_scope` / `residency_verdict` 两行账面）+ 新件 `Cli/ResidencySelfTest.cs`（**10 例自证套件**，真张量夹具，零 shell 零外部进程）+ `Runtime/TensorResidency.cs`（预算语义显式声明 `Ledger.BudgetUnlimited`）。
- **真机证据 · 接前向对账（判据：受限 vs 默认逐位一致）**:
  - tiny（`tiny-gqa-untied.gguf`，3 token）：`--no-pin --budget-bytes 256 --reclaim-per-token` ⇒ `evicts=9 reclaims=12 loads=13 peak_resident=512 budget=256`，`peak = 预算 + 单张量字节`（驱逐确实发生了才可能压到这个值）；**8/8 dump 文件 `cmp` 逐位一致**（logits sha256 `c5bbb3f546a640be`）。
  - 真 7B（4.22 GB）：`--no-pin --budget-bytes 16384` ⇒ **`evicts=118 reclaims=120 loads=121 peak_resident=32768`**；**top-1 = 185 与默认一致**、`logits.bin` sha256 `e34dabd647b50ba0` **逐位相同** ⇒ 驱逐/重载**不改变数值结果**（重物化走同一确定性反量化路径）。
  - 热集常驻（默认 pin 全部 norm）：真 7B `loads=61 hits=60`（第 2 token 起 60/61 命中）、常驻 **999,424 B ≈ 0.023%** 模型体积。
- **自证套件 10/10（真 7B + tiny 双夹具，`residency --selftest <gguf>`，exit 0）**: 预算约束上界 / LRU 驱逐真发生 / **LRU 受害者次序** / **真释放判别** / 账本恒等式 `loaded == resident + reclaimed` / pin 免疫 / 流窗口零物化（量化权重驻留恒 0）/ `ReclaimAll` 释放额精确 / **负控①**全 pin + 预算 1B ⇒ 必须 `evicts=0` 且如实报 `budget_exceeded_honest` / **负控②** 预算语义只声明一次。
- **本轮修掉的两处真缺陷（均为"两层口径不一致"，非表面 bug）**: ① `EnforceBudget` 首行 `if (Ledger.BudgetBytes <= 0) return;`（0 = 无上限）与 CLI 判语 `peak <= budgetBytes`（0 预算 = 必然超限）**各自解释同一个数字** ⇒ `--budget-mb 0` 时账面同时出现"无上限未驱逐"与 `budget_exceeded_honest`。修法：语义**只声明一次**（`Ledger.BudgetUnlimited = budget <= 0`），判定与打印**同源派生**，并补 `--budget-bytes` 表达真子张量级预算（0/负 不再是唯一能表达"很小"的手段）。② **自证断言本身写错**：LRU 次序原在 12 次取用**之后**判定，而 `small[1]` 早已被后续驱逐 ⇒ 断言误红；改为**在驱逐发生的那一刻**判定（事后观测会被后续驱逐掩盖）—— 记入"机检须在事件时刻判定"的可复用教训。
- **诚实边界**: ① 本机 2 vCPU / ~2.2 GiB 可用内存 ⇒ 预算强度只覆盖"小到能触发驱逐"的量级，**未做长序列下的峰值 RSS 压测**；② 驱逐策略是 **LRU-on-tick**，热集晋升（`IsHot` 访问计数）**在前向里未作为驱逐豁免使用**（前向只在 `--no-pin`/默认 pin 两档间切换，未实装"访问计数晋升为常驻"）；③ `--reclaim-per-token` 后每 token 重物化 norm（`hits` 归 0），是**故意**的对照档，不是默认行为；④ 未做多线程/流水线下的驻留并发安全论证（前向当前单线程）。
- 机检: `residency --selftest` **10/10**（真 7B + tiny 双夹具）；Vulkan/内核回归未受影响；全量测试 **1025/1025**。
- **机检有判别力的当场实证（诚实记录）**: 本轮登记表条目**第一次写错**（把 `evidence_path` 写成"源文件 | 报告"两段式）⇒ `VerificationFormTests.Registry_Exists_And_HasNoViolations` **当场判红**（`evidence_path 不存在`）⇒ 改回单一存在路径 + 新增独立 `evidence_report` 字段复跑全绿。自查不是空断言，本轮由它挡下一次。
- **证据报告（真机输出逐字，45 行）**: `docs/reports/r385/residency-evidence.md`（自证 10 例明细 + tiny/7B 对账 + `cmp` 逐位结果 + 复现命令）。

### R399 (2026-09-13) — 题集加硬(M6) + 跑测数据打点(KPI) + 本机 agent.rover 引擎读数

- **靶点（用户令"用你的推荐方案…不用问询我 + 给 KPI 打点 + 我可以看到具体提升报告"）**: R398 的诚实边界写明"6 题 100% ⇒ 对能力提升零区分度"，且**作弊解仍拿 22.2% 用例级通过率** ⇒ 加硬必须作用在隐藏用例的对抗性上；同时"提升"必须可量化 ⇒ 需把每次真机运行的通过率/耗时/token/失败模式落成台账与前后对比报告。
- **交付**: `eval/probe/tasks.py`(627→853，对抗用例机制 `HARD_INPUTS` + 新陷阱族 `pair_closest_abs_sum` + 见证型数学族)、`eval/probe/grade.py`(300→406，`_verify_witness` 独立验证见证 + `wrong_witness` 失败模式)、`eval/probe/run_probe.py`(380→440，族池接线 + `--families`/`--dump-tasks` + 题集 sha 单口径)、新件 `scripts/kpi_probe.py`(418，台账+对比报告+24 条负控)、`eval/probe/README.md`、`docs/plans/v0.25.0-r399-probe-hardening-and-kpi.md`。
- **加硬三层（可复核）**: ① 每程序族钉死 3–5 条边界输入（全负/单元素/10^9/并列/满字母表…）**只进隐藏集**，不足 3 条即**拒发题**；② 新陷阱族 = "两数之和绝对值最小"（朴素写法在同下标复用/并列取值上翻车）；③ 见证型数学题（`x²≡a mod p`、最小反例）⇒ 判定改为**独立验证见证语义**（最小反例还要复核 `∀m<n` 成立），不比对任何标签。
- **真机读数（同题集 sha 内可比）**: agent 全量批 35/35 用例 = 1.0000、整题 6/6、**56.09s**、8 次 LLM 调用、prompt 21,530 / completion 4,845 / **4,396 tok/题**；定向批（新族）36/36、整题 6/6、215.01s、**11,215 tok/题**；**作弊解 22.2%→6.25% 用例级、整题全对恒 0/3**；`oracle` 0.71s 满分（管线正控）。**结论: 加硬只加硬了"对作弊解的判别力"，对 agent 仍饱和 ⇒ 下轮换维度（多步需落盘/缺信息反问/证明链）**。
- **本轮 6 处真缺陷（含 2 处"口径假设错 ⇒ 空心指标"）**: ① 见证型族**从未被抽到**（题池只取 `MATH_FAMILIES` ⇒ 新功能不可达）② 题集 sha **双口径**（生成 vs `--tasks` 复用）③ KPI 时间窗锚点写反（`ts` 是**结束**时刻，写成 `[ts, ts+elapsed]`）④ 遥测 7 位小数时间戳解析失败被 `except: continue` **静默跳过**（token 全 None 且不报错）⑤ `grade_program` 无 `since` ⇒ 产物新鲜度负控从未跑到（假绿）⑥ **R398 漏下的登记表回归**: `evidence_path` 写成 `';'` 多路径 ⇒ `VerificationFormTests` 判红（全量回归当年跑在登记表改写**之前**）。
- **立规（可复用教训）**: KPI/判定的**口径假设错不会报错，只会把指标变成 None/0** ⇒ 每个窗口/口径都必须配一条"锚点写反必须读不到"的反向负控；任何**证据/登记表改写之后必须立刻跑形式校验**（不能只跑功能回归）。
- 机检: 生成器 **39/39**、判定器 **25/25**、编排器 **18/18**、KPI 打点器 **24/24**、`VerificationFormTests` **6/6**。
- **诚实边界**: ① agent 侧仍 100% ⇒ 题集对能力提升仍无区分度；② 数学题仍只判终值/见证，**不判推理链**；③ 沙箱**不是安全边界**（隔离目录+超时+`-I -B`，**不禁网**）；④ 本机唯一 Vulkan 设备是 llvmpipe 软件 ICD ⇒ 引擎读数**只代表 CPU 路径**；⑤ **agent.rover 目前不是解法后端**（只有 `forward` token→logits，缺 tokenizer/采样/解码环）⇒ 已列为 R400 首要工程项。
- **证据报告**: `docs/reports/r399/r399-m6-hardening-and-kpi-datapoints.md` + 机器生成的 `docs/reports/r399/kpi-probe-r399.md`。

### R400 (2026-09-14) — rover 生成链：分词器 / chat template / 采样 / 解码环（本机引擎可当解法后端的前提）

- **靶点（用户令「继续下轮」+「**注意 rover 也在该一直执行任务规划内**」）**: R399 诚实边界写明「agent.rover 目前**不是解法后端**（只有 `forward` token→logits，缺 tokenizer/采样/解码环）」⇒ 本轮补齐**生成链**，且全程落在任务规划体系内（计划文档 + TaskPlan 节点 `dev-rover-gen` + 长期看板 L8 + 登记表行 + 主报告 §7）。
- **交付**: 新件 `src/agent.rover/token/{ByteUnicode,Pretokenizer,BpeTokenizer,ChatTemplate,TableSnapshot,TokenizerAssets.g.cs}`、`src/agent.rover/infer/Sampler.cs`、`src/agent.rover/cli/GenerateCli.cs`（`tokenize`/`generate` 子命令）、`src/agent/agent.csproj`（共享源编译，纯 BCL）；资产入仓 `eval/rover/tokref/`（表快照 + 5 组夹具 + manifest）；生成器 `scripts/rover_{gen_tokenizer_assets,probe_oracle_predicates,build_tokenizer_fixtures}.py`；测试 `src/agent.tests/Rover{Tokenizer,Sampler}Tests.cs`（22 条）。
- **对账口径（跨实现铁律）**: oracle = HF `tokenizers` 0.23.2（**独立实现**）；**199 encode + 199 预分词 + 2000 压力 + 405 解码**夹具逐条相等；chat 渲染 12/12 与 jinja2（transformers 同引擎同参数）逐字节相等；GGUF 装载路径与表快照路径**同摘要**（`merges_sha256=cb5bed793622288a…`、`tokens_sha256=6e5117ddc01e0cb3…`）⇒ 脱离 4.2 GB 模型可复跑全部对账。
- **本轮 5 处实测修正（都是「看起来对」的失效形态）**:
  ① **.NET Regex 不可用于增补平面字符类** —— 它按 UTF-16 码元解析，`𐐀-𐑏` 被拆成孤立代理项 + 反向区间 ⇒ 静默过量匹配；改为生成器把正则机器解析成**标量区间表**，C# 侧标量扫描。
  ② **区间表必须归一化（排序+合并）** —— CJK 正则原文顺序 `一-龥` `ࠀ-一` `가-퟿` 非升序，首版透传致二分查找漏判（`中अआ文` 被切成 3 片）⇒ 归一化 + 新增自检项「严格升序互不重叠」。
  ③ **`\s?[类]+` 的空白前缀需要回溯** —— 贪婪吞空白后若其后不是类字符，必须退回「不吞空白」，让该空白字符本身作为类成员被匹配（U+3000 同时在空白集与标点/CJK 类内）。
  ④ **判定谓词必须逐阶段隔离探测** —— 用整条流水线探测 `\s` 会被后续 CJK 阶段二次切分干扰（把 Zs 类空白误判为「非 `\s`」）；正确读数：`\s` = 25 码点 = **Unicode White_Space 全集**（全 BMP 穷举），Digits = `{Nd,Nl,No}`（1831/1831，负控 3920 例 **0 违规**）。
  ⑤ **切分集 = `added_tokens` 全体 18 个**（实测与 `special=true` 无关）；`special=true` 的 3 个只影响 `decode(skip_special_tokens=true)` —— 编码切分集与解码跳过集必须**分别入表**。
- **负控常态化（带判别力读数）**: merges 乱序 **41.5%** / 逆序 **56.9%** / 清空 **95.3%**（依赖合并样本 1814），阈值取 30/40/90%；空切分集必红；朴素整片预分词判别 **137/199**。统计只在**依赖合并表**的样本上做 —— 整片命中词表的文本与合并表无关，计入会稀释判别力。
- **负控当场抓到的真 bug**: `Sampler.NextU64` 首版把状态拷进局部再 `ref` ⇒ 随机源**永不前进**（采样退化为恒定输出），由「平坦分布 300 抽取必须出现 >5 个不同 id」的反向控制捕获并修复。
- **真机读数**: GGUF 装载路径 199/199 + 199/199 + 2000/2000 + 405/405（`pass=true`）；`generate --chat` 7B 真跑（逐 token 墙钟 / `tok/s` / 峰值 RSS / 流式字节数，见 `docs/reports/r400/rover-generation-chain.md`）；探针 `solver=rover` 已接线（远端 API 与 rover 同题同判定器，读数标注 `budget_limited`）。
- **诚实边界**: ① 本机 2 vCPU / 无 GPU / 每 token 流式扫 ≈4.0 GiB ⇒ 生成**不可交互**（≈20–33 s/token），本轮交付「链路正确 + 可对账」，性能线属 R401/R402；② chat template 仅支持 `system/user/assistant` 子集，工具调用与 Jinja 全量属 R403；③ 采样器**不含**重复/存在/频率惩罚；④ 探针 `solver=rover` 为**限量 token 口径**（默认 8），不得读作「rover 能力为零」。
- **机检**: 新增 22 条测试全绿；形式校验（`VerificationFormTests` / `DevPlanDocRefTests`）+ 全量回归见本轮报告。

### R403 (2026-09-14) — RoPE 配对约定按 arch 选择：prover7b 长期带病运行的根因（静默错误）

- **发现路径**: 追查 `qwen2.5-math-1.5B-Instruct` 端到端「能跑但乱码」时做排除法 —— 分词（HF `tokenizers` 独立 oracle，6 串逐 id 相同）、量化类型（逐张量直方图，全在支持集）、配置读取（HF `config.json` 的 `rope_theta=10000.0` 与 GGUF 一致，此前误记 1e6）全部洗清；对照臂 prover7b 同提示输出 ` 6, ` ⇒ 通用机制正常。遂审 RoPE 约定。
- **根因**: 引擎只实现了一种 RoPE 配对（`x[i], x[i+n_rot/2]` 半偏移），而**权威源 llama.cpp `llama_model_rope_type()`**（`src/llama-model.cpp:2584`，vendored llama.cpp 源码）规定：`LLM_ARCH_LLAMA`（prover7b 的 arch）⇒ **NORM**（`x[2j], x[2j+1]` 相邻配对），`LLM_ARCH_QWEN2` ⇒ NEOX（半偏移）。⇒ **arch=llama 的模型一直在用错配对**，位置信息错乱且不抛错。
- **影响面**: R400 那句 `gen_text= 2 2 2 2` **不是模型行为，是本缺陷的症状**；prover7b 全部历史输出在新配对下不可信，需重测。
- **交付**: `infer/RopePairing.cs`（枚举 + 由 `llama-arch.cpp` **机械提取**的 41 个 NORM arch 名单 + `FromArch()`，未收录⇒NEOX 与上游 default 一致）、`RopeTable`/`CpuKernels.Rope` 双实现支持两约定、`ModelConfig` 增加 `required RopePairing`、`ForwardCli.rope_check` 增加**约定负控行**；权威判定表存档 `eval/rover/oracle/rope-types.json`。
- **验证（同命令同参数）**: prover7b logits `stdev 2.376802840591207 → 2.48841954302631`（生效）；qwen2 **全部数字逐位不变**（范围隔离）；负控 `rope_pairing_negctl{active=NORM other=NEOX max_abs_diff=3.7959385 verdict=distinct}`；`RoverRopeTests` **7/7**（两种约定金标向量 + 跨实现一致 + 负控 + 频率表不变性 + **实现↔存档逐项机检**）。
- **通用教训（已落 skill）**: 两个自研实现可能**共享同一个约定误解** ⇒ 交叉验证长期绿灯而实际违规。`skills/independent-verification-before-claim` v1.1.0 新增判据 11「约定负控」：约定取值换成另一种合法值结果必须变；约定必须锚定**外部权威**并提取成存档 + 机检。
- **附带产出**: `scripts/gguf_probe_remote.py` 远程 GGUF 兼容性预探（HTTP range 取头部 ~24 MB，判 arch/特性/量化可实现性，先探再下）。实测：`DeepSeek-R1-Distill-Qwen-1.5B` RUNNABLE；`Llama-3.2-1B` RUNNABLE；`Qwen2.5-0.5B`/`SmolLM2-360M` 含 **Q5_0** ⇒ BLOCKED（引擎缺内核）；`Qwen3-0.6B` 含 **56 个 qk_norm** ⇒ BLOCKED。
- **诚实边界**: ① **qwen2 乱码仍未定性**（分词与 RoPE 均已排除 ⇒ 剩 tied 词表 / attn 偏置 / GQA 三条 7B 未覆盖路径；判别实验 `DeepSeek-R1-Distill-Qwen-1.5B`（qwen2 且 untied）已排队）；② 本轮仅重测「平凡续写」，prover7b 解法级重测未做；③ NORM/NEOX 表来自 vendored 上游快照，上游变更需重新提取。
- **报告**: `docs/reports/r403/rope-pairing.md`。

### R417 (2026-09-14) — 探针反饱和：质量「分数」缺失的机制根因是**题集饱和**（天花板效应）

- **发现路径**: 用户问「当前链产出质量不高，需要回流的是你自己的上下文」⇒ 想做「质量→分数」的闭环，先清点探针读数 ⇒ 发现 `probe-agent-seed20260913.json` 与 `probe-m6-agent.json` 的 **agent 与 oracle 同为整题全对 100%**，同题复跑逐族一致 ⇒ 题集对当前链已到天花板，**任何质量分数都恒为满分**。
- **根因（与仪器坏掉的区分）**: 负控 `mutation:hardcode` 仍为整题全对 0 ⇒ 判定器判别力在，是**被测对象到顶**，不是仪器损坏（不区分这两者会误修错地方）。
- **交付**: `eval/probe/tasks.py` 新增 3 族（程序族 7→10）：`topo_min`（字典序最小拓扑序，有环⇒`-1`）、`vm_run`（微型栈机：跳转/栈下溢/地址越界/10000 步上限 ⇒ `ERR`）、`json_mini`（严格 JSON 规范化：仅 6 种转义、uXXXX 解码且码点 ≥0x20、键按码点升序、重复键后者覆盖、输出无空白、非法输入 ⇒ `ERR`）；每族 `ref`/`check` **两条独立实现**双路径验算（1422 例分歧 0）；`HARD_INPUTS` 增 24 条对抗用例；`gen_program_task()` 支持 `tight_gen` ⇒ **每题强制注入 1 条「合 JSON 但不合本规格」隐藏用例**（浮点/NaN/低码点 uXXXX/裸 TAB）；`run_probe.py` 增族专属缺陷注入 `topo_dfs`/`vm_noerr`/`json_loose`；`scripts/dev_return_digest.py` 增 digest §3「探针分数」（整题全对率 + 用例级率 + 失败模式 + **饱和标记**）。
- **读数（正负控成对）**: 正控 oracle `topo_min`+`vm_run` 49/49（4/4 整题全对）、`json_mini` 36/36（2/2）；负控 `topo_dfs` 24/52 整题全对 **0/4**、`vm_noerr` 29/48 **0/4**、`json_loose` 54/72=**0.75 用例级但整题全对 0/4**（这条正是「打分单元必须是整题全对」的反例实证）。
- **真机（AOT `agenthost`）**: agent 在 `topo_min`+`vm_run` 上 **74/74、6/6 整题全对 ⇒ 仍饱和**（单调性论证：旧判定器只会低估 ⇒ 满分读数在修正口径下必然仍满分）。
- **首个非饱和质量分数（`json_mini`，n=3 真机）**: 记录口径 27/54=0.5 用例级、整题全对 0/3；**修正口径 47/54=0.8704、整题全对 1/3**（p001 12/18 漏引号 · p002 18/18 满分 · p003 17/18，唯一失分 = `tight_gen` 强制的裸 TAB 紧用例）。**用例级 87% vs 整题全对 33% 的落差 = 「判分单元必须是整题全对」的实证。**
- **仪器两处真缺陷（真机暴露，已修 + 4 条负控入 selftest 29/29）**: ① 提取器"首个可编译前缀"⇒ 长回复下 10 KB 程序被判成 46 字符注释残片；② `grade_program` 先看退出码 ⇒ stdout 正确但 `sys.exit(1)` 被判 runtime_error。修复 ⇒ `eval/probe/grade.py` 提取分两轮 + 前缀下限 64 字符、分类改 stdout 优先（`exit_nonzero_ok`）。
- **证据卫生缺陷（本轮暴露，下轮修）**: `data/probe/replies/` 无臂命名空间 ⇒ 后一臂覆盖前一臂（topo/vm 臂 p001–p003 已被覆盖）。
- **诚实结论**: 「加难族」这条路本轮**未打破天花板**（链在程序题上比预期强）；质量从「计数」变成「连续分数」仍需**换维度**（每题 tokens / 轮数 / 首次通过率——对饱和题集仍有区分度，且直接对齐用户 KPI 口径）。
- **计划**: `docs/plans/v0.38.0-r417-probe-anti-saturation.md`；证据 `eval/rover/r417/`；登记 `docs/verification-registry.json` `r417.probe-anti-saturation`（L4）。
- **文档缺口（如实登记）**: `docs/improvements.md` 的 **R404–R416 轮节未回填**；`docs/plans/v715_dev_plan.taskplan.json` 只登记到 R412（R413–R417 未登记）。 **R518 机检更正（2026-09-17）**：该登记**过宽** —— R408–R416 轮节实际在位；实测缺口 = R402 / R404 / R405 / R406 / R407 / R417 / R418 / R419（另 R403 排序违例），已于 R518 逐节回填。**旧口径作废**（原文保留留痕，不撤）。

### R418 (2026-09-14) — 探针「过程/成本」维度 KPI：成本读数的根因是**归属缺失**，不是缺字段

- **发现路径**: 承接 R417 结论「质量维度被天花板压住 ⇒ 换维度（每题 tokens / 轮数 / 首次通过率）」⇒ 写提取器后**先在旧归档上试跑**，三份不同 run 读出**完全相同的成本数**。
- **根因**: ① `eval/probe/run_probe.py` 回复名 `%s%s-%s`（`--tag` 默认 `""`）⇒ 同一 solver 的不同臂**写同一路径**（R417 已暴露「覆盖」）；② 无命名空间的旧批次**无法确定性归属** ⇒ 若直接取第一个候选，会给出**看似合理的错数**（比缺读数更坏，因为它会被当成证据）。这与 R407 的「自算错而自洽」同族：**错在归属层，不在解析层**。
- **交付**: 新 `eval/probe/process_metrics.py`（349 行）：质量取**判定器产物**、成本取**归档回复原文**；归属三级 = `reply_ns` 精确名 → **时间窗**（`ts - elapsed_s - 5s … ts + 60s`，取自 probe JSON 的 `ts`/`elapsed_s`）→ 否则 n/a；**窗内多候选判歧义、绝不取第一个**；**n/a 不记 0**、均值剔除 n/a；首次通过率只数 `ok ∧ turn==1`，turn 未知的满分题单列 `first_try_unknown`（保守）。`run_probe.py` 归档名带 seed 命名空间（`agents20260916-p001.txt`）+ 摘要记 `reply_ns`。digest §3 增成本列，**质量与成本拼成同一行**（tokens/题、tokens/满分题、turn≤、墙钟均、过程 n/a）。
- **读数（真机 AOT，`json_mini` n=3 seed=20260916）**: 整题全对 **2/3 = 0.6667**、用例级 **52/53 = 0.9811**、**tokens/题 = 9151.0**（prompt 侧）、tokens/满分题 9189.0、墙钟均 **77.7 s/题**、**turn≤1**（零多轮/零追问）、n/a 0、畸形 0。**成对负控**（`mutation:json_loose` n=4，同 seed）整题全对 **0/4**、用例级 0.7324 ⇒ 判别力仍在；该臂不走 LLM ⇒ 成本记 **4×n/a**（记 0 会伪造「零成本」）。
- **诚实边界**: ① 链不落 `completionTokens` ⇒ 只有 **prompt 侧 + 墙钟**；② 探针为单轮 ⇒ 「轮数」目前主要作**异常检测**，首次通过率与整题全对率同分母（真正区分要等链路出现重试/追问）；③ 旧批次（R413–R417，无命名空间）成本**一律 n/a，不做回填**（回填 = 伪造归属）；④ n=3 小样本，非分布。
- **仪器**: `process_metrics --selftest` **14/14**（含反张冠李戴负控、n/a 分母负控、歧义负控）；判定器 29/29；run_probe 18/18；tasks 45/45；kpi_probe 24/24。TaskPlan 已登记到 R418（**21 节点**，末条 `dev-probe-process-kpi`）。
- **计划**: `docs/plans/v0.39.0-r418-process-kpi.md`；证据 `eval/rover/r418/`；登记 `docs/verification-registry.json` `r418.probe-process-kpi`（L4）。

### R419 (2026-09-14) — 探针多轮化：轮数/首次通过率/修复率从「恒等判据」变「可分化」

- **目标**: 让「轮数 / 首次通过率 / 修复率」产生**真分化**（此前单轮 ⇒ 轮数恒 1、首次通过率 ≡ 整题全对率，无区分度）。
- **落地**: `--turns>1` 用**同 sid 跨进程**续上下文（决定性微实验: turn1「记住 4271」→ turn2 命中）；口径铁律 = 轮数取**发送次数 / 归档文件数**（转录里的 `turn N` 是**进程内**轮次，两个进程都写 turn 1）；修正轮默认 **`onfail`**（只对首轮未过题发 ⇒ 前提为真）。
- **三个真缺陷（每个都成对配闸）**: ① 判定器 `run_code` 严格按 UTF-8 解码被测程序输出 ⇒ 程序打印一个坏字节（`0xe9`）即整臂 `UnicodeDecodeError` 崩掉（实测 `STEP_EXIT_agent=1`）⇒ 改字节捕获 + `errors="replace"` + `bad_encoding` 计数（grade selftest 29→31）；② **同 NS 重跑静默覆盖既有读数**（★ 一次真分化读数因此只剩会话记录）⇒ `REFUSE_NS_COLLISION` 闸；③ 首轮失败在日志里不可见 + `reply_chars` 恒 0（归档 11.9 KB 而摘要写 0）⇒ 首轮行原样打印 + 集中回填（run_probe 25→26）。
- **对照臂（假前提）**: `correction=always` 对已达标题谎称「隐藏用例没过」⇒ 首轮 0.6667 → 两轮 **0.0**、回归 **2 题**。教训: **修正轮的前提必须为真**，否则量到的不是「修复率」而是「抗误导性」。产物归档 `eval/rover/r419/evidence-always-correction/`。
- **真机读数（AOT agenthost，`json_mini` n=6 seed=419/420，turns=2 onfail）**: 4 次跑中 **3 次首轮即全对（饱和 ⇒ 判 EXIT 2，不放行）**、**1 次 first=0.8333(5/6) → 两轮 1.0、fix=1.0、回归 0、轮数 7/7 ≠ 6 ⇒ 真分化**（该次产物被同 NS 重跑覆盖 ⇒ 仅会话记录，见 `eval/rover/r419/README-evidence.md`「归档事故」）。
- **控制臂（判别力）**: `mutation:delayfix` **fix=1.0** / `mutation:nofix` **fix=0.0**（三批 n=3/6/6 全成立）；轮数**实到 == 期望**（3/3、6/6、12/12）；检查器 7 态自证（正常0/饱和2/混批3/负控误读2/缺字段3/回归2/NS不符3）。
- **仪器**: run_probe **26/26** · grade **31/31** · process_metrics **22/22** · 检查器自证 **7/7** · tasks 45/45。
- **诚实边界**: 真机侧**未稳定复现**分化 ⇒ 「仪器可用 + 存在分化」**不等于**「r1 链增益已确证」；n=6 单族非分布；`json_mini` 对该链近天花板（R417 的 1/3 读数系**旧提取器**退化所致，提取器修好后分数上移）。
- **计划**: `docs/plans/v0.40.0-r419-probe-multiturn.md`；证据 `eval/rover/r419/README-evidence.md`；登记 `docs/verification-registry.json` → `r419.probe-multiturn`（L4）；TaskPlan **22 节点**（末条 `dev-probe-multiturn`）。

### R420 (2026-09-14) — 「API 落地 ≠ 已接线」：`/recall` 生产消费点（回填：本轮产物已 commit，轮节补记）

- **目标**: `SessionHistorySearch`（R370 交付）在生产里**消费点为 0** —— 能力存在但无人调用，属于「交付完成」的假象。接到本地指令出口 `/recall`。
- **交付**: `src/agent/registry/LocalCommandResult.cs`（`KnownCommands += /recall` + `TryRoute` 臂，四表同步）；`src/agent/IndustrialAgentV2.cs` 宿主 dispatch 特判渲染 + `recall_query` 通道级打点；`SessionHistorySearch.Render`（空命中显式文案，失败可见不静默）；测试 +`CommandRouteConsistencyTests` `/recall` 行 + `SessionHistorySearchTests` 3 条渲染断言（28/28）。
- **真机两臂（L4）**: 治疗臂 `recall_query` 3 事件 / `llm_call` **0**；负控臂（**接线前** AOT 产物）同形输入 `recall_query` **0** / `llm_call` 1 且 stdout **无**渲染 ⇒ 「接线生效且本地指令零 LLM」。C4∧C5 合取才算成立（只有 C4 时，CLI 恒定打印的「意图分析/管线执行」进度行会让人误以为走了 LLM 主链）。
- **诚实边界**: 负控是「接线前 AOT 产物」级而非源码回滚；真机查询 3+4 条非分布；**`hits=0/2` 的质量读数暴露词面重叠缺陷（`不存在`→2 命中）**，登记为下轮候选（→ R421）。
- **计划/证据/登记**: `docs/plans/v0.41.0-r420-recall-wiring.md`；`eval/capability/r420/README-evidence.md`（L4）。

### R421 (2026-09-14) — 跨会话检索的**否定极性**：`/recall 不存在` 不再召回到只断言「存在」的文档

- **发现路径**: R420 的真机**质量**读数（`/recall 外星词根zzq不存在` → 2 命中）不是「没接通」，而是「接通了但答反了」——命中文档全部在断言**肯定**命题（`若图中存在拓扑序…`）。先复现再改码。
- **根因（词元层）**: `Tokenize` 把 `不存在` 切成 `不存`+`存在`，与库里的 `存在` **同词元**；打分为 `score = Σ Idf(t)/√|qSet|`，对否定**无感** ⇒ 否定被丢掉。用受控读数逐位验证公式（n=3、`df(存在)=3` ⇒ `0.5596`；`0.5596/√2=0.3957`；`0.5596/√6=0.2285`）⇒ 缺陷定位在词元层，不在解析/归属层（区别于 R407/R418 的「归属层错误」）。
- **交付**: `Tokenize` 否定标记（`不 没 未 无 非`）自身及其紧邻 1 个二元组带极性问题（`'\u0001'`；`Normalize` 丢弃全部控制字符 ⇒ 真实文本不可产出 ⇒ 无碰撞）；**查询侧与文档侧同一个 `Tokenize`**（对称性铁律：只做词元身份区分，无查询侧特判）；`Render` 片段行补 `AppendLine`；`+6` 单测。（19/19）
- **真机两臂（L4，同 harness、逐字节相同语料 sha256 已录）**:

  | 查询 | 治疗臂 `/tmp/pub_r421` | 负控臂 = **R420 产物快照** `/tmp/pub_r420_pre` |
  |---|---|---|
  | `存在` | 3 命中（`0.5596`，两个真实正样本） | 3 命中（同） |
  | `不存在` | **0** | **3**（`0.3957`）← 缺陷 |
  | `外星词根zzq不存在` | **0** | **3**（`0.2285`）← 缺陷 |
  | `zzq` | 0 | 0 |

  `llm_call` 两臂全查询 **0**；每查询 `recall_query` 恰 1；语料跑后**未被写**。13/13 判据 PASS。
- **两个仪器缺陷（都是「读数不可信」类，不是被测不达标）**: ① `Render` 把命中行与片段**粘成一行** ⇒ 任何按行解析的读数**只能取到第 1 条**（本轮 harness 第一版就这么把治疗臂读成 1 命中）⇒ 补 `AppendLine` + 单测「行可寻址」；② R420 记录的「`存在`/`不存在` 分数同为 1.5660」**不可复现**（实测 0.5596 vs 0.3957；真正相同的是**命中集合**）⇒ 口径更正，结论不变。
- **全量套件**: 1176/0/0（第 3 次跑）。**同一套件前两次各出 1 条顺序/并行相关假红**（`TelemetryPendingTests`；把本轮改动 stash 掉的**基线跑**里则是 `FrontendHandshakeTests`）⇒ 假红与 R421 无关，但「全量绿」这一读数目前**不可一次性复现**，登记为仪器候选。
- **诚实边界**: 极性作用域仅「否定标记 + 紧邻 1 个二元组」（句中远距否定未测）；`别/勿/莫/甭` **有意排除**（`别` 与 `识别/区别/特别` 碰撞）；`无/非` 复合词（`无线/非常`）碰撞致召回损失**未量化**；**打分无长度归一 ⇒ 同一词元命中的所有文档同分（本轮三份同为 0.5596），命中集内无相关度区分度**（登记 R422）；样本 3 文档/4 查询非分布；**主线 KPI（r1 管道增益 / 一轮 token −30%）本轮未触碰**——`/recall` 是本地确定性指令，`llm_call==0` 恰说明它**不产生**远端调用（是不必要调用的抑制器，不是 token 下降的直接贡献者）。
- **计划/证据/登记**: `docs/plans/v0.42.0-r421-polarity.md`；`eval/capability/r421/README-evidence.md`（L4）；`docs/verification-registry.json` → `r421.recall-negation-polarity`；TaskPlan **24 节点**（补登 `dev-recall-wiring` + `dev-recall-negation-polarity`）。


## R431 — role 额外数据（成长经历）挂载进 r1 门判：可机检 + 有界 + 无截断

> 文档缺口声明：本文件条目止于 R421，R422–R430 的权威记录在各自 `eval/rover/rNNN/README-evidence.md` 与「能力」目录；
> 未在此补写（不凭记忆回填读数）。本轮起恢复逐轮追加。

- **因果链**: 用户令「利用 r1 对真假信息判别（记得要挂载 role 的额外数据）」→ 前置机检发现真机角色 `skeptic.rbin` 解出键为 `['id','name','profile','tokens']`（**无 growth 键**）且调用点 `JudgeTurnAsync(content, roleSeed, **null**, ct)` → 挂载在真实负载上是**空操作**（管道本身早已支持：`BuildPrompt` 内 `Clip(growthBlock,300)`）→ 本轮把 null 换成 `GrowthLedger?.RenderForPrompt()`，并让「挂没挂」由遥测读数直接判定，而非「代码里有这行」。
- **产出**: `src/agent/IndustrialAgentV2.cs`（挂载点 + 4 项形状遥测 + `role_growth_domains`）；`src/agent.modelqueue/ModelQueueRouter.cs`（prompt 只构造一次，形状取自实发文本）；`src/agent.modelqueue/LocalGenerationPort.cs`（`TurnGateCounters.LastPromptChars/LastRoleSeedChars/LastGrowthChars/LastGrowthLines`）；`src/agent.roles/RoleGrowthLedger.cs`（`DomainCount`）；`src/agent.tests/TurnGateGrowthMountTests.cs`（**9 条**机检）；`docs/plans/v0.52.0-r431-growth-mount.md`；`eval/rover/r431/`（precheck/frozen_baseline/settle_r431/make_evidence + 双臂读数）。
- **基线对比**（同二进制 `sha256 ac62a739…`，字节 15,184,624，**IL 告警 0**，V0 形态闸 PASS）:
  | 臂 | 启动域数 | 门判 prompt_len | growth_chars(行) | 判定 | 远端调用 | 远端 tokens | 闭合/截断 |
  |---|---|---|---|---|---|---|---|
  | `-g431` 挂载（fixture 3 域） | 3 | `[426,426,426,426]` | `[70,70,70,70]`(3) | Skip×4 | 1 | 2030 | true / 无 |
  | `-b431` 对照（真角色 0 域） | 0 | `[355,388,388,388]` | `[0,32,32,32]`(1) | Skip×4 | 1 | 1994 | true / 无 |
  | R430 基线（挂载前） | — | 无该字段 | 0（未挂载） | Skip×4 | 1 | 1996 | — / — |
  测试(对侧 r431 节原记): 新增类 9/9；**全量 1251/0/0**（第 2 次跑；第 1 次 1250 通过 + `TelemetryPendingTests` 1 红，单跑 2/2 通过 ⇒ R421 已登记的仪器假红，与本轮改动无关）。
- **关键读数**: prompt 长度差恒等于 `块长+1`（挂载追加一个换行）—— 单测不变量与真机读数一致（355+70+1=426）；对照臂第 2 次门判起出现 32 字符/1 行，来自链自产账本（`IndustrialAgentV2.cs:1684`）⇒ 接线消费的是**链自己积累的**角色数据。
- **诚实边界**: **本轮不宣称 token 下降**（`k8r` 是重复认可族，本不产生额外远端调用；2030/1994/1996 同量级）—— ≥30% 验收需**真假信息判别网格**（假信息/纠错族），未跑；「有成长域时 r1 判得更准」**未测**（只测了生效/有界/不截断/判定不翻转）；`role_growth_domains` 仅启动配置行读一次，运行中新增域看 `growth_chars_seq`；对照臂 = 「角色无域」而非「代码不挂载」（干净对照是 R430 基线的 null 路径，已由引擎复算逐位证明）。
- **下轮候选**: ① 真假信息判别网格（P 族假信息/纠错），量化挂载对判定准确率与远端调用数的影响（≥30% 验证主战场）；② 遥测补 `growth_sha16`，把未挂载臂「同长」升级为「同指纹」；③ `role_growth_domains` 逐轮携带。
- **计划/证据/登记**: `docs/plans/v0.52.0-r431-growth-mount.md`；`eval/rover/r431/README-evidence.md`（L3）；`docs/verification-registry.json` → `r431.gate-role-growth-mount`。

## R434 — 前置门质量硬线: 「真假判别网格」P 族 + r1-Skip 双条件结构修 (2026-09-14)

- **因果链**（按文档走）: `docs/improvements.md` R431 节「下轮候选 ①」逐字指定「真假信息判别网格（P 族假信息/纠错），量化挂载对判定准确率与远端调用数的影响（≥30% 验证主战场）」 ⇒ 本轮预注册 `docs/plans/v0.55.0-r434-falseinfo-discrimination-grid.md`（判据 C1–C7）后执行。**机检前提**: 机械前置门把「?/问句词/诉求词/纠正词/数字/≥24 字符」全部结构性 Pass ⇒ r1 **只在残余带（无机械信号的短消息）判别** ⇒ P 族题集 8 个测量轮全部落在带内（机检 8/8 `MechanicalPass=false`）。
- **产出（分相）**:
  - Phase 1 基线（AOT `/tmp/pub_r434`, HEAD `69d405c`, IL=0）: 分母臂 A = 8 主答调用/**18493 tok**; 治疗臂 B(挂载域=3) = 2 主答调用/**4958 tok**（**降幅 73.2%**）; 对照臂 B0(域=0) 9535; 无设备臂 BP 19465（跳过 0）；复跑臂 B2 与 B **逐位一致**。
  - **质量硬线失守**: 4 个真诉求轮里 **3 个被 r1 判 Skip ⇒ 用户拿到空话**（`再讲一遍。`/`讲细一点。`/`从头再说。`）⇒ C2 ✗。
  - Phase 2（少样本修）**被实测证伪**: 门判两条 P 例 `另外，测试命令是什么？`/`不对，你上一轮不准确，请重新确认。` **全带机械信号**、生产里到不了本门 ⇒ 带内只剩 S 例 ⇒ r1 学成「短消息 ⇒ S」。补两条带内 P 例后 prompt 实测 +28 字符（425→453）但臂 B 判定**逐位不变**（B0 由 0.625→0.875）⇒ 不作修法。
  - Phase 3（**双条件结构修**，定稿 AOT `/tmp/pub_r434d` sha `54e30c19…`, IL=0）: `Skip 生效 ⇔ r1 判 Skip ∧ MechanicalAck(用户原文)`，非认可族一律降级 `Pass`（`gate:skip_rejected_nonack→remote`，新增 `SkipRejected` 计数 + `local_turn_gate_reject` 事件）。方向性 = **白名单**（承认哪些可省）⇒ 任何误判只可能多花 token，**不可能让真诉求变空话**。
- **基线对比**（同网格 `task-p8`；外部真值 = 桩逐请求 tokens + 逐轮回复来源；内容锚定+顺序分区 `unassigned=0`；通道分离 G 主答/J 判官）:
  | 臂 | 主答调用 | 判官调用 | 总 tok | 相对 A | 假阴性 | 假阳性 | 判定准确率 |
  |---|---|---|---|---|---|---|---|
  | A 门关（分母） | 8 | 0 | 18493 | — | — | — | — |
  | B 挂载（域3）修前 | 2 | 7 | 4958 | 73.2% | **3** | 0 | 0.625 |
  | **B 挂载 修后** | 5 | 7 | **12338** | **33.3%** | **0** | **0** | **1.000** |
  | B0 未挂载 修后 | 5 | 7 | 12163 | 34.2% | 0 | 0 | 1.000 |
  | BP 无设备（负控） | 8 | 7 | 19465 | -5.3% | — | — | 跳过 0 次 |
  | BRJ 单变量（判官本地优先） | 5 | 6 | 12288 | 33.6% | 0 | 0 | 1.000 |
  | **扩族 task-p12**（12 轮, 含带内假断言/带外假断言/纠错）A | 11 | 0 | 27670 | — | — | — | — |
  | 扩族 task-p12 B（挂载） | 7 | 8 | 19990 | **27.8%** | 0 | 0 | 1.000 |
  判据: C1 ✓（IL=0；两外部真值通道；带内机检 8/8）/ **C2 ✓（假阴性 0）** / **C3 ✓（假阳性 0）** / **C4 ✓（33.3% ≥ 30%）** / C5 ✗（挂载无增益，且压制示例敏感度） / C6 ✓（无设备 ⇒ 跳过 0） / C7 ✓（逐位复现）。
- **测试状态（R434 定稿）**: 全量 **1267 项 / 1266 绿 / 1 红** —— 红项 = `TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure`（**已登记仪器假红**: `AgentTelemetry` 为静态类 + 测试类并行 ⇒ Configure 顺序竞态）; 单跑该类 **2/2 绿**; **排除实验**: 以 `--filter FullyQualifiedName!~产物遥测键契约` 复跑仍 1 红 ⇒ 与本轮改动**无因果**（不是本轮引入）。
- **机器不变量（新增测试）**: `G30` 门判示例**每个 tag 至少一条落在残余带内**（带外示例对 r1 不可见）；`G31` 认可族判定表（正向 5/反向 8，含「再讲一遍。」族）；`G32` 链侧必须接线。对侧冻结基线与 R434 重冻结留痕（355/`8749b0a1…` → 383/`2dcfe801…`，+28 逐字节可核）。
- **诚实边界**: ① 单机单次（除 B 的两批复跑）；② **代价已披露**：质量硬线恢复使降幅由 73.2% 降到 33.3%（换掉「错跳真诉求」的省法）；③ C5 挂载贡献为负/无 ⇒ 本族**不宣称挂载增益**；④ 认可族白名单保守 ⇒ `好，按这个来。` 这类带内真·认可也会走远端（只多花 token）；⑤ **J 通道（更正）**: 关系判官本地优先，但 `local.relation_judge` **默认 false** ⇒ 默认远端（本轮臂全为 false，8 次判官全部 remote ≈341–375 tok）；单变量臂 **BRJ**(=true) 实测 8 次判官仅 **1 次 local 成功**、**6 次 remote_fallback**（字母取到桩文本）⇒ 「J 本地化」**未达成**；桩不产出合法字母 ⇒ J 的**收益**在本器具下不可测，只报开销；⑥ 轮 4（`好的，明白。`）在**全部臂**被产品澄清 ask 消费 ⇒ 测量轮 = 8 而非 9；⑦ 单族 8 轮，外推需另跑；⑧ 门判遥测 `basis` 已改为反映**最终判决**（修前会写 r1 原始判决 ⇒ R433 同类「读数自报假形态」风险消除）。
- **候选推进台账（用户令: 所有候选无疑问则全推进）**: ① 双条件结构修 **达成**；② 门判示例带内不变量 **达成（结构）**；③ 挂载增益 **负结论**；④ J 本地化 **未达成**（local 1/7）；⑤ 门禁复位（对侧 R431 行）**达成**（全量 1266/0/0）；⑥ TaskPlan 回填 R430–R434 **达成**（30→35 节点）；⑦ 题集扩族（`task-p12`, 12 轮含带内假断言/带外假断言/纠错）**达成（含负结论）**: 质量判据全绿（假阴性 0 ∧ 假阳性 0 ∧ acc 1.000, 带内假断言被双条件救回）但 **降幅 27.8% < 30%** ⇒ 主判据在低认可占比题集上不成立（预注册 §14 已列风险）⇒ 宣称收窄「≥30% 依赖认可轮占比」，**未调题集凑数**；⑧ `code_source`/产物通道**达成（契约钉死）**: 生产端与判分端两侧机检测试（`script_artifact` 的 path/compile_valid/origin/sha8/exit + `grade.py` 消费点），防 R433 假红重生。
- **下轮候选**: ① J 判官 prompt 可解析性（本地 1/7 的根因: 查 raw/error，或改判定形式/预算）——「不必要的 API 请求」最大残余；② 认可族白名单扩容（`好，按这个来。`/`照你说的办。` 等），须以**成对判据**（假阴性=0 ∧ 假阳性=0）为准；③ 题集扩族（假信息断言/多轮纠错/跨域）以检验外推；④ R433 遗留 `code_source`/产物通道写入产品侧遥测契约；⑤ 门禁/登记表复用（本轮已复位对侧 R431 行 `evidence_path`/`covers`）。
- **计划/证据/登记**: `docs/plans/v0.55.0-r434-falseinfo-discrimination-grid.md`；`eval/rover/r434/README-evidence.md`（L3）；`docs/verification-registry.json` → `r434.turn-gate-double-condition`；`eval/capability/kpi.jsonl` 末行 R434。


### R435（2026-09-14）关系判官（J 通道）本地化：真机 1/7 → 5/6

- **用户令（逐字）**: 「利用r1对真假信息判别…让用户一轮任务总数tokens使用量显著下降30%以上(主要是不必要的llm api请求少了)」⇒ 本轮攻 R434b 负结论「J 本地 1/7」= 不必要远端调用最大残差。
- **推进台账（用户令: 所有候选无疑问则全推进）**: ① prompt 形状（承重）**达成**: 本地可解析 1/6 → 5/6（真机 6 例，非空 prev），远端判官调用 6 → 1；② 失败原因遥测 `local_state` **达成**（R434 归因缺口闭环）；③ 空 `previousReply` ⇒ 结构性 Neutral **达成**（确定性规则，0 模型调用，消掉 turn1 的必失败例）；④ 解析层加固（64 字尾窗 + 判定词表 + 负控）**达成但非承重**（四臂 old≡new）；⑤ 预算 512→1024 **负结论（已回退）**（A1≡A2、A5≡A4 逐例相同，turn5/turn9 在 1024 仍耗尽 67.8s）；⑥ 端到端 token KPI（≥30%）**未测** ⇒ 下轮承重。
- **方法学要点**: ① 先取证: 产品遥测 8 条 + 忠实探针 A0 复现 1/7（**耗时逐例对齐** 18.09↔20.407s…9.76↔9.894s，pred=149=tokens=149）⇒ 器具可信后才改码；② 单变量六臂矩阵（prompt 形状 × 预算 × 解析层）；③ 反教考同一: v2 实例**不用 grid 原句**；④ prompt 单一构造点 `BuildJudgePrompt`（本地/远端同一输入面，结构上不可能两套提示）。
- **自纠（必须披露）**: 探针 think 标记手打混入 **U+200B** ⇒ `close` 恒 False ⇒ 分类器读思考链 ⇒ 假阳性 8/9（与产品 1/7 冲突暴露）；改由**源码程序化派生 + 长度/码位断言**。另: 同会话覆盖未 commit 的计划案 ⇒ 原 pre-registered 阈值不可恢复，相关阈值改标 `checks_posthoc`。
- **下轮候选**: ① **端到端 BRJ 网格重跑**（新 AOT 二进制）测 ≥30% token 判据（承重）；② turn9 类「思考链无界」（停发词/思考长度约束）；③ turn7 类 A/N 边界（同族实例）；④ 门+判官**合并单次本地调用**（省一次 prefill，性能向）。
- **计划/证据/登记**: `docs/plans/v0.56.0-r435-relation-judge-localization.md`；`eval/rover/r435/`（probe_j1..j4 + reclass_j2 + probe-j{2,3,4}-classified.json）；`src/agent.tests/RelationJudgeParseTests.cs`（18/18）；`eval/capability/kpi.jsonl` → R435。

### R436（2026-09-15）端到端 BRJ 网格重跑：承重 token 降幅 29.28%（p12）/ 34.41%（p8）

- **用户令（逐字）**: 「利用r1对真假信息判别…让用户一轮任务总数tokens使用量显著下降30%以上(主要是不必要的llm api请求少了)」⇒ 本轮承重 = R435 新 AOT 二进制端到端重跑（R435 §7 候选①）。
- **推进台账（用户令: 所有候选无疑问则全推进）**: ① **端到端 BRJ 网格重跑（承重）达成（含负结论）**: J 本地化自 R434 登记 **1/7（本地成功）** 提升至 **7/7 全本地**；远端判官请求 `7` 次 → **0**；p12 降幅 27.8% → **29.28%**（+1.48 pt）但 **< 30.0%**（差 0.72 pt）⇒ 承重未达；p8（可跳散布）=34.41%（达标）；② 判据 C1–C8 逐项机器判定（`verdict-summary.json`）**达成**；③ 器具加固: J 标记**程序化派生**（源码字面量 + 无不可见码位断言）替代手打（R435 U+200B 教训）**达成**；④ 归档复现控制 S1（同标记重跑 R434 五份 calls ⇒ G/J 计数逐臂一致）**达成**；⑤ 确定性复跑（BRJ#2 Δtoken=7）**达成**。
- **基线对比（同二进制 sha16 `45c37dd5b88ffcf2`；外部真值 = 桩逐请求 tokens + 遥测双源；通道分离 G 主答/J 判官）**:

  | 臂（task-p12） | 主答调用 | 判官远端 | 判官本地 | 总 tok | 相对 A | 假阴性 | 假阳性 | acc |
  |---|---|---|---|---|---|---|---|---|
  | A 门关（分母） | 11 | 0 | 0 | 27654 | — | 0 | 4 | 0.6363636363636364 |
  | B 门开+J 远端 | 14 | 7 | 0 | 20633 | 25.39% | 0 | 0 | 1.0 |
  | **BRJ 门开+J 本地** | 7 | 0 | 7 | **19557** | **29.28%** | **0** | **0** | **1.0** |
  | BRJ#2 复跑 | 7 | 0 | 7 | 19564 | — | 0 | 0 | 1.0 |
  | BP 无设备（负控） | 18 | 7 | 0 | 29569 | -6.92% | 0 | 4 | 0.6363636363636364 |
  | p8: A → BRJ | 8 → 6 | 0 → 1 | 5 | 18481 → 12122 | **34.41%** | 0 | 0 | 1.0 |

- **降幅分解（同二进制, 单变量）**: 门（跳过 4 个早簇认可轮）= A→B 25.39%；J 本地化（消除 7 次远端判官调用）= 1083 tok = 3.92 pt ⇒ 合计 29.28%。
- **自纠（必须披露）**: ① 本轮 settle 器具首发崩溃（归档 verdict 字段名 key 缺失）⇒ 修脚本 + **离线重结算**（原始 calls/遥测全部在盘, 未重跑臂）; ② S2 交叉定义首版错误（把 `source!=local ∧ prompt_len==0` 的**结构性判定**当成远端请求）⇒ 按实测分类学收紧为 `prompt_len>0`; ③ AOT 发布**非逐字节可复现**（同源两次发布差 325 字节, BuildID 不同）⇒ 二进制 sha 不可当源码状态指纹; ④ 本侧发布窗与对侧 60m 自检作业（23:55 写 R437 分析行）重叠 ⇒ 已登记, 未改他方产物。
- **诚实边界**: ① 远端 token 为**桩侧估算**（非真实计费）; ② 未真机重放远端（桩返回固定话术 ⇒ 臂 B 的远端判官字母无意义, 故 B 的 acc 不代表真机）; ③ 本地判官 1301 tok（7 次）不计入 API token 但非零成本（串行 139 s）; ④ ≥30% **未**在 p12 达成 ⇒ 宣称收窄「≥30% 依赖可跳轮占比**与位置**（早簇最不利）」。
- **对侧交叉（R437 模型, 不改他方产物）**: 对侧 R437 预测 J 修复 +1.1…+1.9 pt（p12 28.8–29.6）⇒ 本轮实测 +1.48 pt **落在该带内**。
- **下轮候选**: ① V1–V5 长度分档实测（对侧 R437 §7 已预注册; 需先空出测量窗）; ② p12 型早簇构成下要 ≥30% ⇒ 降单次主答 prompt（上下文/记忆段按轮压缩 或 role 块瘦身）; ③ turn9 类「思考链无界」（R435 遗留）; ④ 门+判官合并为单次本地调用（省一次冷启动）。
- **计划/证据/登记**: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md`；`eval/rover/r436/README-evidence.md`；`docs/verification-registry.json` → `r436.e2e-brj-token-kpi`；`eval/capability/kpi.jsonl` → R436。

## R439 — 修复的域扩展验证：长任务 V20(20 轮) + p8 复测（零源码改动）

- **承重读数（远端 API token 降幅）**：p8 37.9%（严口径 G+J；G 口径 38.74%）、**V20 45.31%**（G 口径 45.81%）、p12 37.37%（R438）。三条网格 ≥30% ⇒ R438 修复非 p12 特例，且**降幅随任务长度上升**（长网格 45.3%）。
- **口径纠正（诚实登记）**：R436 台账 p8 的 34.41% 用「G+J」总量计；判官本地化口径下 **G-only=38.74% / 严口径=37.90%**（pre-fix G-only 为 35.25%）。修复本身贡献 +3.49pt（p8）。
- **预注册 → 实测**：跑前预测（01:51 落盘）p8 39.28% / V20 42.37%；实测偏差 **−1.38pt / +2.94pt**（均 ≤3pt 容差）。A 臂跑完后锚定预测 V20 45.37% → 偏差 −0.06pt（**该文件被 cp 覆盖后于 02:13 重生成，时序证据弱化，已登记在案**）。结构模型（A 逐调用曲线 + 角色块偏移 δ(i) + 跳过块质量 m(t)）在**真外样本** p8 上复现 BRJ 总量偏 0.73%（p12 0.0%）；V20 分母外推只差 −0.4%。
- **门质量**：p8/V20 fn=0, fp=0, acc=1.0（7 个 ack 轮全跳 / 13 个带内真诉求全通）⇒ 省钱没有靠错杀真诉求换来。
- **A 臂分母不变性**：p8 A 复跑 = R436 = 18481 tok（逐位相同）⇒ 对比可跨轮使用。
- **诚实边界**：无设备负控(BP)本轮未跑（V20 净增量未测，沿用 R438 p12 −6.92%）；BRJ 同臂复跑未做；桩外部真值不含 provider 缓存/计费；V20 判官本地成功率 11/13（2 次远端回退 310 tok，已计入）。
- **器具**：`eval/rover/r439/{predict_r439.py,design_check.py,agg_r439.py,run_all.sh,grid/task-V20.json}`；设计审计器为 Python 第二实现，对 p8/p12 的机械判定与 C# 实测逐轮全等（自证）；证据档 `eval/rover/r439/README-evidence.md`。

## R438 — 本地消化轮不得回放「从未发出的」内联块（缺陷修复，p12 越线 37.37%）

- **因果链**: `IndustrialAgentV2.cs:1267` 在**门判定之前**无条件 `message.SentContent = sentUserContent`（含本轮内联块）
  → 门判 `Skip` 的轮次**没有任何远端调用**（块从未离开本机）→ `GetConversationHistoryAsync:2670` 按 `SentContent ?? Content`
  把它落进会话历史 → 此后**每一次**远端调用都逐字回放这些从未发出的块。修复 = 跳过分支把 `SentContent` 归位为 `outboundText`。
- **缓存红线为何不受影响（先拆前提）**: R379「发送字节=回放字节」的语义域是**已发送字节**；本地消化轮无发送字节，
  其条目位于 provider 已缓存前缀**之后** ⇒ 剥离不改变任何已缓存字节。
- **臂矩阵（p12, 12 轮, 同一 AOT 二进制）**:

| 臂 | 调用 G/J | r1 skip | AOT token | 降幅 vs A | FN/FP/acc |
|---|---|---|---|---|---|
| A 关闸基线 | 11/0 | 0 | 27654 | 0.0% | 0/4/0.636 |
| **BRJ 门+J本地+修复** | 7/0 | 4 | **17319** | **37.37%** | 0/0/1.000 |
| BRJ2 同臂复跑 | 7/0 | 4 | 17326 | 37.35% | 0/0/1.000 |
| BP 无设备负控 | 11/7 | 0 | 29569 | −6.92% | 0/4/0.636 |

- **预注册命中**: `predict_r438.py`（逐字节重放 R436 冻结 calls + 同估算器）预测 **37.37%**，实测 **37.37%**（偏离 0.0 pt）。
- **因果归因**: 同臂 BRJ 相对 R436 档案 19557 → 17319 = **−2238 tok**，且逐调用 token 差与「条目字符差/2」最大偏离 **0.0** ⇒ 全部差异就是被移除的块。
- **不变量机检（新器具）**: 相邻远端调用「前一次请求是后一次的逐字前缀」— A 10/10 对、BRJ 6/6 对、**0 违例**（把 R379 红线从注释变成判据）。
- **泄漏形状**: BRJ 跳过轮 [2,3,4,5] 泄漏块 = **0**，24/24 条目逐字等于机检派生的用户原文；臂 A（无跳过轮）逐调用读数与 R436 **完全相同** ⇒ 无附带效应。
- **确定性**: Δ=7 tok（0.040%），残差**完整归因** = 系统提示内嵌 run 目录路径长度差 2 字符（非模型抖动）。
- **自纠（必须披露）**: ① verify 首版 C6 过严（把「首轮无前序上下文 ⇒ 块为空」误判为缺块）⇒ 加首轮免检并用 R436 档案反证该豁免**先前就存在**（A 11/11、BRJ 7/7 首轮条目无块）; ② 首版 C7 要求逐调用读数全同（真机本地生成回复长度可变）⇒ 改「决策全同 + Δ≤0.5% + 残差可归因」。
- **诚实边界**: ① 远端 token 为**桩侧估算**非真实计费; ② 未真机重放远端; ③ **本轮未跑 p8**（承重已由 p12 达成，p8 属外推）; ④ 前缀单调性只覆盖桩侧请求序列，**provider 真实命中率未测**; ⑤ 本地 r1 成本 1301 tok/139 s 串行不计入 API token 但非零。
- **下轮候选**: ① p8 + 长度分档 V1–V5 复测（≥30% 的域扩展）; ② 排查其它零远端调用路径是否仍写 `SentContent`; ③ 门+判官合并为单次本地调用（省一次冷启动，R435 遗留）; ④ turn9 类「思考链无界」。
- **计划/证据/登记**: `docs/plans/v0.58.0-r438-localskip-no-replay.md`；`eval/rover/r438/README-evidence.md`；`docs/verification-registry.json` → R438；`eval/capability/kpi.jsonl` → R438。

## R441 收益窗口下界 + 位置曲线补点（2026-09-15，零源码改动，同网格实测 A 分母）

- **靶点**: R440 留下了两个未定项 —— ①「≥30%」宣称的**下界**在哪 ②R440 C7「位置效应符号被证伪」（预注册给 −1.2pt，实测 +3.26pt）。本轮用 4 网格 8 臂 + 2 个复现对收口。
- **网格**: W8(N=8, 可跳 1/8, 末轮) / W20(N=20, 可跳 1/20, 末轮) / M20(N=20, 可跳 7/20 **中簇 t7–13**) / V2b(N=4, 可跳 1/4)；**全部使用同网格实测 A 分母**（不再用跨网格代理）。
- **读数**: W8 **13.77%**（17260→14884）、W20 **3.20%**（54326→52590）、M20 **46.19%**（61230→32950）、V2b **32.24%**（6126→4151）。
- **窗口下界**: **单次 realized skip 即转正**（+3.20% 起）⇒ 「≥30%」需要约 7/20 可跳比（中簇 46.19%、晚簇 48.57%），或小任务 1/4 可跳比（32.24%）。零可跳 20 轮仍净亏 −2.40%（R440 V5 存档）。
- **位置曲线**: 散布 45.31 < 中簇 46.19 < 晚簇 48.57 ⇒ 单调、跨度 3.26pt ⇒ R440 C7 应改述为「位置效应**符号为正、幅度小**」。
- **质量**: 非跳轮回复**逐位相同** 42/42（W8 7、W20 19、M20 13、V2b 3）；跳轮回复 = 本地消化族文本（常量从 `src/agent.modelqueue/ModelQueueRouter.cs` 程序化派生，禁手打）。
- **复现**: 跨轮 V2b(-c2) vs R440 V2b(-b1) **逐位相同**（调用序列 + 回复文本 + Δtot=0）；同轮 W8 双跑 13.77% vs 13.76%（Δ0.011pt，残差=NS 后缀使工作区路径长 3 字符 ⇒ +1~+2 tok/轮，进 system prompt）。
- **预注册判据 6/8 通过**: C1/C4/C5/C6/C7/C8 OK，**C2/C3 FAIL**。根因均在**器具/模型**，非链功能:
  - C2: W8 前 7 轮逐位相同 ✓；W20 前 13 轮中 5 轮 +1 tok = 工作区路径长度伪影（`run-A-W20` 比 `run-A-V4` 长 1 字符）。
  - C3: ① **预测器代理 A 未按网格长度 N 截断** ⇒ W8 分母取 V4 全长 61281（应 17260）⇒ 修好后命中 13.18%（ρ=0 13.42%）vs 实测 13.77%。② **块质量 m 不是位置函数而是会话累积状态函数**（M20: t7≈94 → t17≈197 tok）⇒ 改用同网格实测（`blockmass_r441.py`）后 M20 残差 3.79pt → **1.77pt**。
- **δ 律收窄（R440 结论的修正）**: δ=77 tok 只对**主调用**成立、且只在 t≤13 成立；t≥14 逐轮增量升到 **156/193/270/347/418**（B 臂 block 内嵌累积 [已完成] 列表 ⇒ 与位置同增）。
- **新发现（两臂块不对称，入 debt）**: BRJ 臂内联块携带累积 `[已完成]` 列表，A 臂同位置是 `[Memory (RAG)]`/`[联想]` 行 ⇒ 两臂块**不同源**，使实测降幅**偏保守**（W20: 模型 5.74% vs 实测 3.20%；差 2.55pt 主要来自 B 臂 t≥14 块膨胀）。
- **跳轮微步骤成本 ρ 无确定触发**: 同二进制同网格下 ρ∈{0, 41} 都出现（W8/M20/V2b=0，W20=41）。
- **诚实边界**: ① 口径 = 远端 G 调用 (prompt+completion) 之和，**本地 r1 token 不计入**（与 R436–R440 同口径）；若计入则降幅显著变负。② 未测真实 API 计费/时延。③ r1 判官单轮耗时 24–40s（落 `run-*.log`）未纳入 KPI。④ C2/C3 未过，**不得宣称预注册全绿**。⑤ 阶段二脚本把网格误当第 4 位置参数 ⇒ 顺带产出复现对（缺陷已登记）。
- **下轮候选**:
  1. **R442：两臂块不对称定量** — 同网格对比「B 臂块累积 [已完成] vs 关闭累积」，量化保守偏差（预期回收 1–3pt）。
  2. **R442：ρ 触发条件定位** — W20 型（末轮单跳）与 M20 型（中簇多跳）各跑 3 次，统计 ρ 分布与簇长/位置相关性。
  3. **R443：口径钉死** — 明确「用户一轮总 tokens」是否含本地 r1；若含须给折算规则，否则 ≥30% 宣称口径不成立。
  4. **R443：A 分母截断回归闸** — 把 `a_map_proxy` 的 N 截断写成 `design_check` 的机械断言 D7，防同类器具缺陷复发。
- **计划/证据/登记**: `docs/plans/v0.61.0-r441-gain-window-floor-and-position-curve.md`；`eval/rover/r441/README-evidence.md`；`docs/verification-registry.json` → `r441.gain-window-floor-and-position-curve`；`eval/capability/kpi.jsonl` → R441。


## R445 — 判官侧机械前置：**可分性预检为负**（零测量轮）
- 器具 `eval/rover/r445/judge_prefilter_precheck.py`（标记表程序化派生自 `CorrectionDetector.cs`；三控齐备）。
- 读数：541 判官行 / 244 行真机 r1 实答（排除 297 行桩回声、0 行未对齐、60 run）。
- C1（无标记 ⇒ Neutral）**FAIL k=124**；C3（len≤16）**FAIL k=5**；C2/C4 空心通过（s=0）；C5 负控 k=128；C6 正控 30/30；C7 rc=2。
- 结论：**判官侧不存在消息面廉价必要条件**（归档范围内）⇒ R444 候选 ① 不可实现，登记为负结论（`docs/verification-registry.json` r445.*）。
- 附带发现（事后）：同一消息跨 run 拿到不同 verdict（7 条，`好，按这个来。` 三态并存）⇒ 赏罚信号不稳，是质量缺陷而非 token 缺陷。

### 下轮候选（R446，按优先级）
1. **判官降级消融**：短 prompt / 更小 maxTokens / 去 `CorrectionDetector.cs:143` 空内容翻倍重试 ⇒ 真机测本地 tok 降幅 + 与归档 244 行裁决一致率（对照基线已落盘）。
2. **修赏罚信号不稳**：把高信采纳词扩展到 `好，`/`行，`/`可以，` 前缀+短消息形态（0 token 结算），用 244 行做回归。
3. 把 R445 三控并入 `eval/capability/instruments-check.json` 常规器具面。
4. 结构性短路只可扩展「上一轮回答空 ∨ 会话首轮」（已实现），其余需真机 A/B，禁止凭离线推。

## R447 — 判官解码侧约束（单字母 GBNF）等价性消融：**负结论**（真机探针，零产品代码改动）
- 靶（承 R446 机制结论）: 判官本地成本 = 预填充 2764 + **生成 1974**（M20 全本地真值 7841）；猜测「生成占 ~42% ⇒ 解码侧强制单字母可省 ~1.9k tok」。本轮只做**等价性真机消融**，不改产品。
- 器具: `eval/rover/r447/`（语料 v2 = 12 遥测真值对 + 6 golden 真值对；prompt **源码派生**，忠实性闸对 golden **9/9 逐字**同）；4 臂 J0(基线 512,temp0,无约束) / J1(prompt 不变 + `grammar=root ::= "A"|"C"|"N"`, n_predict 8) / J2(只砍预算 8) / NC1(错配 prev) + posthoc NC1b(真错配)。
- 读数（`verdict-r447.json`）: C1 PASS（可解析 0.944/1.0）｜**C2 PASS**（`gen` 均值 **178.6 → 2.0**，比值 0.0112；墙钟 15.75s→5.6s）｜**C3 FAIL**（`agree(J1,J0)=0.4444`，**J1 = 18/18 恒 `A`**）｜C4a FAIL（**判定项设计缺陷**：prev 候选仅 2 常量 ⇒ 8 条只有 2 条真错配）｜C4b PASS（恒 N 0.3889）｜C4c PASS（J0 与归档产品字母 **12/12**）｜C5/C6 PASS（`cache_n≡0`、argv/请求体逐字段自证）。
- J2 侧证: 18/18 `thinking_truncated`（8 tok 全被思考吃掉）⇒ 「只砍预算不约束解码」必然解析失败 ⇒ 产品会 fallback 远端，反而更贵。
- 事后判据: CH1 真错配 prev（8/8 真错配）把一致率从 **1.0 → 0.5** ⇒ 基线确实依赖 prev（器具非空心）；CH2 语法臂 vs 产品真值 0.5；**CH3 登记型发现**：J0 有 **1/18 触 512 上限**未吐字母（`从头再说。`）⇒ 现网预算 512 并非总是足够（白付 512 本地 tok 再 fallback）。
- 机制结论: **思考是判官判决的承重结构**。强制首 token 后模型不再做判决、恒定吐 `A`（=其首 token 先验）⇒ 解码侧生成约束**不可用于判官**。
- 诚实边界: ①单模型档/单容器；②语料 msg 全 ≤18 字符、prev 真值仅 3 种 ⇒ 等价性证据 **msg 面强、prev 面弱**；③C5 恒等式一项未测；④C4a 为判定项缺陷（**不得宣称预注册全绿**）；⑤门通道（同构，生成 ~130 tok/调用 ×7）未测；⑥无链跑 ⇒ **不写 kpi.jsonl**；零产品代码改动 ⇒ 无 AOT/测试对象。
- 登记: `docs/verification-registry.json` → `r447.judge-decode-constraint-grammar`；证据 `eval/rover/r447/README-evidence.md`；计划 `docs/plans/v0.67.0-r447-judge-decode-constraint.md`。

### 下轮候选（R448，按优先级）
1. **判官 prompt 侧「限长思考」消融**（不取消思考：`思考不超过 2 句，随后另起一行只写一个字母` + `n_predict 128`）：靶 = 生成 178→≤64 / 与归档真值一致率 ≥0.9 / 消掉 1/18 截断（CH3）。
2. **门通道同构消融**（`local_turn_gate`，生成 ~130 tok ×7 调用）：先只读机制复现，再与判官同臂。
3. **预算档扫描**（256/384/512）对截断率与 fallback 率的影响（判官 + 门联测）。
4. **把「prev 候选数 ≥3 + 真错配断言」写成语料构建器机械闸**，防 C4a 同类判定项缺陷复发。

## R448 — 判官 prompt 侧「限长思考」消融：**负结论**（真机探针，零产品代码改动）

- 靶（承 R446 机制 + R447 负结论）: 本地判官成本 = 预填充 2764 + **生成 1974**（M20 全本地真值 7841）；R447 已判死「解码侧强制单字母」（取消思考 ⇒ 恒 A、不等价）。本轮独剩的形态 = **保留思考、只限其长度**（prompt 插入「思考最多 2 句 (不超过 40 字), 不要展开推理。」，`n_predict` 128）。
- 臂（同语料 18 对，解码档钉死 temp 0）：`J0` 产品 prompt/512（本轮重跑基线）｜`T2` 限长 prompt/**512**（隔离 prompt 单独效应）｜`T1` 限长 prompt/**128**｜`NC1t` T1 配置 + **真错配 prev**（8 对）。
- 读数（`verdict-r448.json`）: J0 gen 均值 **178.6**（median 169，max 512，Σ3215）；**T2 138.5**（median 138.5，max 211，0/18 截断）；**T1 119.7**（median 128 = 触顶，**截断 11/18 = 61.1%**，另有 1 条空结论 ⇒ 可解析率 **0.3333**）。
- 判据 6 红: **C1 非空心 FAIL**（T1 可解析 0.3333）｜**C2 生成降幅 FAIL**（比值 0.6702 > 0.36）｜**C3 prompt 单独效应 FAIL**（T2 比值 0.7755 > 0.75 **且** agree(T2,J0)=0.4444）｜**C4 等价 FAIL**（agree(T1,J0)=0.1667、agree(T1,归档)=0.1667）｜**C5 截断闭合 FAIL**（T1 11 条 vs 目标 0）｜**C7 记账 FAIL**（判定项设计缺陷，见下）。**C6 负控 PASS**。
- 机制结论: **该 1.5b 蒸馏模型的思考长度不受 prompt 指令控制**（限长子句下真实长度仍 median 138.5 / max 211），而在判官通道里**思考是判决的承重结构**（改一字即刻改判决：T2 与 J0 判决一致率仅 0.4444）⇒ 压思考=改判决=不等价；只压预算=截断=产品必然 fallback 远端=**更贵**。**本地生成侧无可用的压缩通道**（R447 解码约束 + R448 prompt 限长，两条均因不等价关闭）。
- 收益上限（反事实，不计入 KPI）: 即便强行启用，判官生成按 0.67 折算 ⇒ M20「含本地真值」口径仅 33.32% → **34.38%**（+1.06 pt）⇒ 收益与风险不成比例。
- 器具机械闸（承 R447 候选 4，新建立即生效）: G1 独立重建 18/18 与快照逐字节相同｜G1b 忠实性 9/9 产品实发原文｜G2 prev 面多样性下界（distinct=3、>25 字符 1 条——**只钉下界不宣称强**）｜**G3 负控真错配 8/8**（直接封死 R447 C4a 那类「判定项设计缺陷」）。
- 自纠（必须披露）: ① 分析器 C6 判据写成 `(ag_NC or 1) <= 0.85`，`agree=0.0` 被 `or` 吞掉成 1.0 ⇒ 首版误判 FAIL；已修并重跑（C6 转 PASS）。② C7 预注册含「逐样本 prompt_n 跨臂相等」——但 T 臂 prompt 比 J0 长 28 字符（正是被消融的自变量）⇒ 该断言按定义不可能成立（0/18），属**判定项设计缺陷**；已按判据纪律**保留 C7 红、单列** CH6 修正口径（T2 vs T1 **18/18** 相等 + cache/恒等式/argv 全绿）。
- 诚实边界: ① 单模型档（`r1-distill-1.5b-q4km`）+ 单容器（`-c 4608`）；② 语料 msg 全 ≤18 字符、prev 真值仅 3 种（**prev 面弱**，G2 只钉下界）；③ 口径 = 本地 llama-server 真值 token，**未转成**用户可见的远端 API 计费；④ 未做远端 A/B（等价已红 ⇒ 无必要）；⑤ 门通道（`local_turn_gate` ~130 tok/调用 ×7）**本轮未测**；⑥ 无链跑 ⇒ **不写 `eval/capability/kpi.jsonl`**；零产品代码改动 ⇒ 无 AOT/测试对象。
- 登记: `docs/verification-registry.json` → `r448.judge-think-length-cap`；证据 `eval/rover/r448/README-evidence.md`；计划 `docs/plans/v0.68.0-r448-judge-think-length-cap.md`。

### 下轮候选（R449，按优先级）
1. **预填充侧压缩**（2764 tok/10 调用 = M20 判官成本的 58%）：判官 prompt head 含 3 条例式示例 → 逐条删减/改述的**等价性**真机消融（同臂 J0 对照 + 归档第三通道 + G3 真错配负控）。← 首选（本地降本仅剩的两条通道之一，且与生成侧无关）
2. **判官 + 门合并为单次本地调用**（R435/R438 遗留候选）：省一次冷启动与一次预填充；先只读复现两通道 prompt 形状与调用次数（判官 10 / 门 7，M20）。
3. **门通道同构消融**（`local_turn_gate` 生成 ~130 tok ×7）：先只读机制复现，再与判官同臂。
4. **把「判定项设计缺陷」前置成器具闸**：预注册里凡出现「跨臂相等」类断言，构建器须先机检该断言在**臂定义层面**可满足（本轮 C7 / R447 C4a 同类错误两次复发 ⇒ 升为通用闸）。

## R449（2026-09-15）· think-memory 开关交付 + 真实流量外部通道结案

用户裁定：think-memory 加开关；「用户↔agent 对话即真实流量」且**有效性须筛选**；用性价比最高的方案落地；**state.db 数据若无法提 KPI 则结案回归主线**。

- **交付（源码/测试）**：`src/agent.exploration/ThinkMemory.cs` 新增 `ThinkMemorySwitch` 四档（env `AGENTFRAMEWORK_THINK_MEMORY` = `on` 默认 / `off` / `recall0` / `write0`）；`off` 档三闸 = 不读盘 / 不落盘（库文件 mtime 不变，可机检）/ 不改库；`Recall` 首行 `RecordRecallAttempt()`（反空心）；`HitCount` 与「refs 采纳次数」分离（修「命中恒 0」根因）；**宿主零改动**。测试：`ThinkMemorySwitchTests` 26 条 + `TurnGateParseTests` 13 用例（跨语言同位夹具）⇒ 定向 **33/33**、全量 **1321/1321 绿**；AOT 重发布（**收尾轮实测**：rc=0 / IL 警告 0 / 15,201,152 B / sha16 `fa3292068970740a` / V0 形态闸 PASS）。
- **收尾轮修补 G1（开关可观测性）**：计划 §4 机检② 预注册「`think_memory_boot` 必带 `enabled/mode/loaded`」，首版只发 `embedder_injected/available/instance` ⇒ 开关只改行为不可观测、判据 C5 无从机检；已在 `IndustrialAgentV2.cs:429` **加性**补齐 `mode/enabled/loaded/records`。AOT 形态三臂机检（`eval/rover/r449/verify_boot_telemetry.py` → `verdict-boot-telemetry.json`）**V1–V5 + 器具负控 10/10 PASS**：OFF `mode=off/enabled=false/loaded=0/records=0` ＋ 库文件跑前跑后逐位相同；ON `mode=on/loaded=1342/records=1342`（**成对** ⇒ 证明 OFF 的 0 是短路读盘而非库空）；NC-TEL（`AGENTFRAMEWORK_TELEMETRY=off`）读不到 boot 记录 ⇒ 用具具判别力。边界：三臂均 `/exit` 空转 ⇒ 只覆盖启动期档位，运行期差异化仍只有 JIT 单测；未测 `recall0/write0` 档 AOT 读数。
- **通道结案**（`eval/rover/r449/verdict-r449-close.json`）：**`STATE_DB_CANNOT_IMPROVE_KPI`**。承重证据（机械、与判官无关）：`可跳轮 = Ack ∧ ¬MechanicalPass` ⇒ state.db 1,542 轮中 ack **0/1542**、`gate_eligible` **0/1542** ⇒ 远端降幅实现额 **0**；语义侧：用户 OOB 实证「认可类消息 = 批准继续执行」⇒「认可 ⇒ 可跳远端」前提不成立。
- **判官探针 VOID**（预注册判据 I1 3/7 < 5/7、I2 0/13 < 9/13）：产品同网格自身读数 7 Skip + 3 reject + 8 Pass、`raw_len 127..515`，探针 `gen=6` 无思考 ⇒ 生成形态失锚（seed sha16 逐位对齐 `0aa656fa7eafd93a`、模板源码 `git diff` 空）⇒ 真实流量判官读数一律 **n/a**（R380：没测到 ≠ 失败）。
- **事后读数**（`checks_posthoc`，不得引用为产品结论）：D 类 S 63.3%（19/30）、S 53.8%、O 28.6%、加权 33.4%；退化率 D 45% / S 58.3% / O 25%。
- **器具缺陷 3 处**（已修，登记于计划 §10）：`labels` 三元组误用 `dict()`；`csharp_unescape` 不解 `\uXXXX`（think 标记被派生成 15/16 字符 ⇒ 解析必走尾部窗口）；`POST /props` 误用（501，该端点仅 GET）。
- **登记**：`docs/verification-registry.json` → `r449.think-memory-switch`(L2) / `r449.turn-gate-parse-crosslang-fixture`(L2) / `r449.real-traffic-external-validity`(L3)；证据 `eval/rover/r449/README-evidence.md` §6；计划 `docs/plans/v0.69.0-r449-think-memory-switch-and-external-truth-channel.md` §10–11。
- **诚实边界**：① 语料 = 用户↔Hermes agent 对话（≠ 产品终端分布，通道 A1 需部署端日志）；② 判官侧读数因失锚作废 ⇒ 本轮无真机远端 A/B；③ `real-corpus.jsonl`（21.6 MB，含真实文本）不入库；④ 无链跑 ⇒ 不写 `eval/capability/kpi.jsonl`。

### 下轮候选（R450，按优先级）
1. **判官输入侧特征块 A/B**（用户建议的 NLP 前置）：同批真实样本 × {原始文本, 结构化特征块}，判据 = 退化率 / 判决分布 / 单调用 token；
2. **器具锚改「产品实发 prompt 落盘」**（新增 `--gate-prompt-dump`）——本轮失锚的根因对策，并给门通道加「源锚版本」闸；
3. 残留：`本地口径降幅 V5/V1 净亏`、`15x 决定性实验`、doc HTML 报告 T8。

## R450（2026-09-15）· 门判实发 prompt 落盘锚：器具失锚定案 + AOT 两条硬教训

用户指令：把输入输出的数据预处理成 r1 能很好识别的数据（**先修锚**，否则任何输入友好化实验都会重复 R449 的 VOID）。

- **交付**：`ModelQueueRouter` 加 `AGENTFRAMEWORK_GATE_PROMPT_DUMP`（默认关=零产品变更；JSONL `seq/len/sha16/prompt`；**UTF8 无 BOM**；**零反射手写 JSON 转义**）。
- **失锚定案**：`derive_template()` 越界把 3 个插值标签（`【角色设定】`+`【用户消息】`+`答案:` = 恰好 **16 字符**）抽进模板，`build_prompt()` 再追加 ⇒ R449 探针实发 = **标签重复的畸形 prompt**（产品永不产生）⇒ `gen=6` 无思考、正控 3/7、I2 0/13。三处独立读数（R443 记录 / 遥测长度代数 / 修正后实测）= tpl **280**。
- **逐位锚建立**：修正后与产品**实发文本**比对 —— 同成长态条目 **delta=0（453 字符逐位相同）**；其余条目首差异**全部落在成长块计数**（`赏6/罚0` vs `赏8/罚1`/`赏9/罚1`/`赏11/罚1`）⇒ 残余差 = **会话累积态**（可归因、可机检）。
- **默认档零变更（实机背书）**：开档跑 M20 ⇒ `tokens_total = 32968`（= R444 BRJ 原值）、`gate_r1_n = 7`、`r1_skips = 7`、`r1_passes = 0`、`accuracy = 1.0`、`repro_archive_ok = true`。
- **AOT 两条硬教训（本轮实发）**：① STJ **反射**序列化在 AOT 被禁用（实测 `InvalidOperationException`）⇒ 仪器必须零反射；② `Encoding.UTF8` 建文件**写 BOM** ⇒ 下游 JSONL 解析器炸，必须 `new UTF8Encoding(false)`。两条都**由仪器自己在日志留告警 / 在 s1 首跑暴露**，否则会静默产出空证据（"没测到"伪装成"测过"）。
- 器具：`GatePromptDumpTests` 4/4；全量 **1323/1325**（2 个**环境型偶发红**：① `ExecutorHardeningTests.FileLock_ConcurrentAppend_NoLoss_NoInterleave` 期望 120 实际 119，单跑 **3/3 绿**；② `TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure`，与已知「残留 host 进程写遥测 ⇒ 假红」同源。**两个均须在无在飞执行体时复跑定性**，不得当"已绿"报）。
- 登记：`r450.gate-prompt-anchor`(L2)；计划 `docs/plans/v0.70.0-r450-gate-prompt-anchor.md` §6；证据 `eval/rover/r450/anchor-r450.json`、`dump-BRJ-M20-s2.jsonl`。

### R451（2026-09-15）· 真实流量探针重跑（器具锚修复后）：**再判 VOID，但失锚被逐出模板段**
- 判决 `VOID_INSTRUMENT`（`eval/rover/r451/verdict-r451.json`）：I1 正控 **3/7**（需 ≥5/7）⇒ 真实流量读数一律 **n/a**（I4 闸，与 R449 同处置）。
- **正面进展**：文本层锚**成立** —— `tpl_len=280`（== R443 记录）、`seed_sha16=0aa656fa7eafd93a` 逐位相同、17 条 pin 对残余 delta ∈ [−3,+12] **全落成长块**（会话累积态）⇒ R450 修的越界 +16 已闭合，**prompt 文本不再是失锚嫌疑**。
- **残余失锚（本轮新定位）= 调用/解码面**：同一份对齐文本下，产品同 7 条 = **7/7 Skip**，探针 = **3/7 S**；探针 ack 行两种形态（`gen=6` 裸字母 / `gen=512` 复读 prompt 自身结构「用户消息：…答案：S」）⇒ 模型处于**续写文档**而非**助手作答**模式。可疑差异：聊天模板应用方式/端点、采样与 `n_predict`/stop、上下文尺寸。
- **反空心（两控成对直接兑现）**：I2 平凡通过（13 条非认可 11/13 判 P）**不构成证据** —— 同调用面下判官近似恒定 P（认可族也只 3/7 放行）⇒ 判别力不足，只有 I1 能拦下。
- 器具：`real_gate_probe.py --ns r451`（NS 参数本轮新增，避免覆盖 R449 的 VOID 证据）；偏差声明：`MemAvailable 2587 < 2650` ⇒ **读数前**下修 `-c 3584`（探针 prompt<600tok、gen≤512，语义不变）。
- 登记：`r451.real-traffic-reprobe`(L2)；计划 `docs/plans/v0.71.0-r451-real-traffic-reprobe.md` §6；证据 `eval/rover/r451/{verdict-r451.json,probe-real.jsonl}`。

### R452（2026-09-15）· 弃重建、**产品自身跑真实语料**（零重建路线）：真实流量读数落定
- **路线变更**：R449/R451 的「重建 prompt」探针两度 VOID ⇒ 改由**产品自身**发 prompt、做判决、写遥测（锚自动成立）。三臂：`RC`（M20 网格正控）/ `RP`（真实 51 轮·生产配置）/ `RJ`（真实 51 轮·前置门关=判官强制）。
- **P1 PASS（外部效度真读数）**：生产配置下真实流量 **门 r1 = 0、Skip = 0**（36 门事件全 `mechanical`）⇒ 用户钦定的「一轮任务 token ↓≥30%（少发不必需远端请求）」在**真实分布上实现额 = 0**。
- **一等发现①（守卫承重）**：判官强制面 **14 次 r1 调用全投 S 票，14/14 被机械认可族守卫否决**（`gate:skip_rejected_nonack`），其中 **13 票落在「继续下一轮」**（用户钦定的驱动类）⇒ 若守卫缺失，这 13 轮会被本地跳答 = **用户指令不被执行**。R444 的 `Skip ⇒ Ack` 等价性前置在真实数据上直接兑现安全价值。
- **一等发现②（门判输入面）**：门判 prompt **不含 prev 段**（`【用户消息】… 答案:`）⇒ **门判 = f(msg)**（修正预注册的 f(msg,prev) 框定）；prod 的 14 票 S 全部落在此面。
- **一等发现③（真实省 token 通道）**：**吞并轮 7/51 = 13.7% 远端调用为 0**（计划复用/澄清应答吸收）——与门无关，是真实分布上唯一有量级的「少发远端请求」来源。
- **真实收益口径**：生产行为省下的是 14 次**本地**门判 r1 = 7,204 tok/51 轮 ≈ 141 tok/轮（本地算力，非远端 API token）。
- **正控复现**：`RC-c2` **32,961** vs R450 `s2` **32,968**（Δ −7 tok = −0.02%，字符估算舍入级）、7/7 Skip、逐轮 `actual` 序列**逐位相同**。
- **器具缺陷（本轮实发）**：`RC-c1` 的 39,364 = 我的「按前 64 字符前缀」匹配器**跨语料误命中**（网格短轮命中真实轮 ⇒ 桩吐 160 字符真实回复）⇒ 加 `R452_MATCH=0` 修正并重跑 ⇒ `-c1` 读数**作废**；教训 = 「按输入文本对齐的重放器具，匹配键必须限定本次语料，且必须有已知期望值的正控」。
- 交付：`eval/rover/r452/{prereg-r452.json,summary-r452.json,verdict-RC-M20-c1/-c2,verdict-RP-REAL-p1,verdict-RJ-REAL-j1,dump-RJ-REAL-j1.jsonl}`；计划 `docs/plans/v0.72.0-r452-product-native-real-traffic.md`；登记 `r452.product-native-real-traffic`(L2)。零 `src/` 变更。

### R453（2026-09-15）· 真实分布 KPI 通道台账 + 「吞并轮」通道审计（**零产品变更**）
- **问题**：R452 已定真实流量可跳面 = 0 ⇒ 必须（a）冻结真实 token 账，（b）找出真实分布上唯一有量级的省远端调用通道。
- **读数（R452 RP 臂 = 真实 51 轮·生产配置）**：吞并轮 **7/51 = 13.7%**（全部 `G_calls=0`；形状 `param_slot_fill` 6 / `clarify_ask` 1）⇒ **上界**省 **54,852 tok = 14.0%**（均价 7,836 tok/调用）；远端 50 调用/391,800 tok；前置门省 **14 次本地 r1 = 7,204 tok**；可跳面 = 0（判官 S 票 14/14 被守卫否决）。
- **判据机检**：P1 吸收轮 ⇔ `G_calls==0`（结构性不变量）PASS；P2 子集关系 PASS；P3 ≤16% 上界 PASS（14.0%）；P4 禁质量宣称 PASS；`verdict-r453.json` rc=0。
- **缺陷信号（描述性，不作因果断言）**：下一轮重复同一条消息 `[12,31]`；下一轮含抱怨词 `[33,44]`；驱动类短语被吸收 `[12]`；长消息被吸收 `[2,25,44]`。
- **新登记陷阱**：`eval/rover/**/turns-*.jsonl` 实为**单个 JSON 对象**（写 `run_arm_r452.sh:22`、读 `settle_r444.py:100`）；命名误导但读写两侧自洽 ⇒ 本轮**不改**（改可比性属独立预注册轮）。
- **诚实边界**：省下量是**上界估计**（反事实臂未做）；**质量裁决缺失**（桩回复非真回复）；10 轮 `G_calls=0` 中 **3 轮未归因**（记 n/a）；零产品变更 ⇒ 未重发 AOT、未跑全量。

### R454（2026-09-15）· 外部对照：**codex-cli 0.154.0 vs click-agent**（用户 OOB 钦定：避免无用功）
- **方法**：codex-cli 0.154.0（npm 装 `/tmp/codexenv`）+ 自建 OpenAI/Responses 兼容桩 ⇒ 用 `-c model_providers.stub.{name,base_url,env_key}` 把 codex 接到本地，**捕获它真实发出的请求体**（`codex/req-001.json`，含 `tools` 全量）；同输入 = `继续下一轮`。
- **读数（同输入真实字节）**：codex 静态面 **34,542 B**（instructions 16,979 字符 + tools 17,563 B）、**9 工具**（`exec_command`/`write_stdin`/`request_user_input`/`view_image`/`multi_agent_v1`(namespace 10,178 B)/`get|create|update_goal`/`web_search`）、`store=false`+`prompt_cache_key`+`reasoning.summary=auto`、**wire_api 只剩 responses（chat 已删）**；我方 **4,300 B / 0 工具 / chat.completions / 2 条消息**（`ModelQueueRouter.cs:962-966`）。
- **负控 C5（证伪）**：「codex 好 = prompt 更小」**不成立** —— 它是我们的 **8.0×**。
- **归因**：codex 把能力放在**模型 + 工具面 + 沙箱**（宿主单一循环）；我们把能力做在**宿主**（plan/absorb/门判/判官），远端零工具面 ⇒ 宿主复杂度膨胀 = 「越做越精细」的根因；codex **不做**本地小模型判真假/Skip（与 R449/R452 实测一致）。
- **本轮自我抓到的器具缺陷**：R453 收口的「形式门禁 13/13 绿」是**假绿** —— 过滤器 `FullyQualifiedName~FormalCheck` **匹配 0 个测试**而 `dotnet test` 仍 rc=0。真名 `VerificationFormTests`(+`DevPlanDocRefTests`) ⇒ 复跑 **Failed: 0, Passed: 9, Total: 9**。通用教训入 memory：**门禁必须断言执行数 > 0**。
- **诚实边界**：codex 侧仅 1 次捕获（默认配置、无 AGENTS.md）；我方**未新抓包**（`MemAvailable 2477 < 2650` 内存闸禁起 llama-server）⇒ 已捕获读数 + 源码事实双证；只比请求面/接口面，**不比回答质量**（桩输出非模型输出）。
- 交付：`eval/rover/r454/{compare_codex_clickagent.py,compare-r454.json,codex/*}`；计划 `docs/plans/v0.74.0-r454-codex-external-contrast.md`；报告 `docs/reports/codex-contrast-r454.md`；登记 `r454.codex-external-contrast`(L2)。零 `src/` 变更。

### 下轮（R455）
1. **同题双跑回归**（用户钦定「对照相同输入的返回」）：`codex exec --json`（usage 真值 input/cached/output/reasoning）vs `agenthost`，同模型/同模板/同截断，逐项比 token/工具调用/轮数/成功率 —— 这是「避免无用功」的直接量尺；
2. 若判定补 **P1（远端无工具面）**：给远端请求加最小工具面（read/write/exec + 权限声明）⇒ **独立预注册轮** + AOT 复发布 + 质量 A/B（唯一与 codex 实质对齐的路径）；
3. 遗留：3 轮未归因 `G_calls=0`；关系判官本地成本前置化；主线残留（零可跳档净亏 / 短档 V2b 13.03% / L.7 语言无关令）。

### R455（2026-09-15）· 模块覆盖对照套件 + **agent 链机制诊断**（用户裁定 R454b→R455；**零产品变更**）
- **用户裁定（驱动）**：R454b「单句对照」= **无效数据**（测不了模块/命中率/闸门；codex 6 连次毁基准）⇒ 建「同环境/同输入/逐模块可测」套件。
- **套件**：`eval/rover/r455/run_suite.sh`（双侧 `/tmp/r455_env/{codex,agent}/work` 逐字节同夹具 + 同一 `suite-turns.json` 6 轮 + 同一真模型 `deepseek-flash` + **零重试**）；判分 `judge_suite.py` 只读落盘证据；adapter 透传 codex `tools`。
- **读数（五格全可复核）**：M4 执行 **我方 0/4 vs codex 4/4**（`4` / `ALPHA\nBETA\nGAMMA` / `chars=14` / `R455 fixture note`）；M3 问询 **1 vs 0**；M1 缓存 **86.6% vs 96.6%**；M6 调用 **7 vs 13**、in **18,039 vs 91,002**、out **957 vs 597**；M2 闸门 **n/a**（`MemAvailable<2650MB` ⇒ 不记通过）。
- **一等发现（机制根因，源码级）**：**管道无动作环** —— ① 远端请求体无 `tools`（`ModelQueueRouter.cs:950-1000 SerializeChatRequest()` 只写 `model`/`messages`）；② 全仓 `grep tool_calls`（*.cs）= **0 命中**；③ 唯一执行入口吃的是**用户输入**（`IndustrialAgentV2.cs:633-636 _skillDispatcher.DispatchAsync(message.Content)`）⇒ 模型没有结构化动作出口，可执行任务只能产出**承诺/澄清**，且会**伪造成果**（T2「已完成：count.txt 写入」+ 伪命令行，盘上无文件；T3/T4 断言 x/y/z.txt 不存在 = 幻觉）。
- **KPI 归因**：该缺陷是「一轮任务总 token ↓≥30%（不必要的 LLM 请求少了）」的**反向承重项**（无动作 ⇒ 澄清轮 ⇒ 轮数↑）；**问询次数**升为一等指标。
- **器具修正（诚实）**：① `resume` 用**进程 cwd** 而非记录 cwd ⇒ 首跑 cwd 漂到仓库根（已修：进夹具目录再 resume）；② adapter `response.completed` 必须带 `input_tokens`/`output_tokens`（否则 codex 自连）；③ 判分器期望值须 `norm()` 归一（首判 `merged.txt` 假 FAIL，修 1 行后 codex 4/4）。
- **常态流程入册**：`docs/external-reference-harness.md`（用户钦定「可以将对比流程加入开发文档内」）—— 同环境/同输入/同模型/零重试/单句不算/判分只读落盘/负控成对。
- 交付：`eval/rover/r455/*`、`docs/plans/v0.75.0-r455-codex-capability-ab.md`、`docs/reports/agent-chain-diagnosis-r455.md`、`docs/external-reference-harness.md`；registry `r455.module-coverage-ab`（L2，含 5 条负控）。

### 下轮（R456）· 动作环（Action Loop）：链机制修复（用户钦定「不是关键字/补丁」）
1. **声明面**：按能力注册表派生 `tools[]` 入远端请求（手写 JSON / STJ Source Generator，AOT 零反射），**会话内恒定**以保缓存前缀；
2. **解析面**：解析 `tool_calls` → 映射既有执行面（`SkillScriptRunner` / 文件端口 / `GitOperations`），**零关键字路由**；
3. **回灌面**：`role:"tool"` 结果回灌 + 步数上限 N≤3 + 每步审计落盘（命令/rc/stdout 有界），失败 fail-closed；
4. **验收**：重跑 R455 套件（目标 4/4 产物、0 问询、调用数 ≤ 基线、缓存不退化）+ 越界/超时负控 + AOT 复发布形态自证。

### R456（2026-09-15）· **动作环实施**（机制修复，非关键字补丁；产物 0/4 → 2/4）
1. **声明面**：`ActionToolDecl.ToolsJson` 静态常量（list_dir / read_file / write_file / run_command），AOT 零反射；`QueueChatRequest.ToolsJson` 手写 writer 输出。
2. **解析面**：source-gen DTO 加 `tool_calls` + `finish_reason` → `QueueResponse.ToolCalls`（无 tool_calls 时与旧版行为逐字节一致）。
3. **回灌面**：`QueuePrompt.PostUser` 追加 messages 尾部（前缀不变 ⇒ 缓存前缀单调增长），`SerializeChatRequest` 输出 `tool_calls` / `tool_call_id`。
4. **执行面**：`WorkspaceActionPort`——工作区根约束（越界即拒）、8 KB 输出上限、120 s 超时、进程树回收、UTF8 无 BOM 审计。
5. **E2E（同夹具/同 6 轮/同模型）**：产物 **2/4**（count.txt=4、merged.txt 与 codex 逐字节同）；审计 4 次真实工具执行；**磁盘级伪造「已完成」消失**（R455 有 4 处）；prompt ∑31,537 / 缓存 84.8% / 调用 9（codex 冻结 91,002 / 96.6% / 13）。
6. **器具修复**：`adapter_tools.py::to_chat_tools` 漏认 chat 风工具声明 ⇒ 静默丢弃（假阴性 `tool_calls=null`）；修复后烟测两侧 `finish_reason=tool_calls` ⇒ 模型工具调用能力成立。
7. **残余缺口（R457 候选）**：T4 未落盘 + 口算错（15 vs 14）；T5/T6 被吞并/续跑入口吞掉；缺 API key 时静默空回复（须告警）。
8. 遗留：3 轮未归因 `G_calls=0`；零可跳档净亏；短档 V2b 13.03%；L.7 语言无关令。

### R462-W（2026-09-15）· 本地判别**权重档位探针**（用户令：改用 3B 并删多余模型）
- **口径三面对齐产品**（否则读数作废）：判据面逐行移植 `TurnGateJudge.Parse`（13/13 产品自带用例逐条相等）；调用面对齐 `/apply-template + add_generation_prompt` 链路（n_predict=512/seed=0/cache_prompt=false/-np 1/f32 KV）；语料=产品实发 dump 逐位比对（selftest exit 0）。
- **读数**（28 条 = 14 负类真实驱动消息 + 14 正类真实 Ack）：`1.5b-q4` 假跳 **14/14**（对「继续下一轮」也判 S）· `1.5b-q8` 11/14 · `qwenpaw-2b-q4` 9/14 · **`3b-q4` / `3b-q5` 假跳 0/14、漏跳 0/14、acc 1.000、gen 2.0 tok/次**。
- **根因（机检口径）**：P2 参数档增益 **+0.500** ⇒ 瓶颈=**参数量**；P3 量化档增益 +0.107 ⇒ Q8 救不回 1.5B（零换族方案不成立）。3B 比 1.5B 省本地生成 token **98.7%**（158→2 tok/次），代价 17.5 s→30.5 s/次。
- **负控**：NC1 判据面（自造「首个非空白字符」口径 ⇒ 11 条答案在末尾被误判未解析，v1 读数 VOID）· NC2 调用面（不渲染 ⇒ 复读机且不可复现，v2 读数亦 VOID）· NC3 恒 S 假模型 = 1.5b-q4 实测逐位吻合（复现 R452）· NC4 恒 P 成对 · NC5 确定性（两臂 28/28 项逐位相同）。
- **交付**：`eval/rover/r462/{prereg-r462-w.json,verdict-r462-w.json,bench_r462_w.py,report_r462_w.py,selftest_r462_w.py,corpus-r462-w.json,w/*}`、`docs/reports/r462-weight-probe.md`；registry `r462.weight-probe`（L2）。

### R463 (2026-09-15) · 本地判别通道切 3B + 冗余模型清理（用户令）

状态: 已完成 (commit b18a61b)

- **用户令（逐字）**：「改用3b 并且 删除多余模型 3b q4」。
- **依据**：R462-W 权重档位探针 —— 1.5B-Q4 恒 S（假跳 14/14）不合格；Qwen2.5-3B-Instruct-Q4_K_M 假跳 0/14、gen 2 token/次、确定性 28/28 逐位复现。
- **改动**：① `config/base/models.yaml` 新增顶层 `local:` 块（第 77 行，`turn_gate/relation_judge=true`，ctx 4608 / parallel 1 / max_tokens 512）；② `src/agent.llamacpp/LlamaCppTextGenerator.cs:35` 默认权重名同步；③ 3B 权重落 `~/.agentframework/models/`；④ 删 4 个冗余权重（6.53 GiB，先落 bytes+sha256 台账）。
- **E2E（同网格 p12 / 同桩 / 同 role / 同二进制，7 臂）**：A 分母 12 调用/31,093 tok；**B3B 8 调用/20,487 tok ⇒ 降幅 34.11%**；B15 与 B3B **逐位同读数**（前置门开时模型档位无差异 ⇒ 承重的是机械 Ack 规则）；前置门关 B15pf0 真诉求假跳 3 次（守卫否决 3）vs B3Bpf0 **0 次**；BP2 真负控（双缺模型）全降级 Pass、降幅 −7.1%。
- **质量**：7 臂 12/12 轮 ok、残余带/纠正轮零 Skip（quality_risk=0）。
- **契约边界修订**：`FreeApiModelsTests.Yaml_Stripped_OfRemovedSources` 原「禁 `\nlocal:`」断言与 R351 口径澄清冲突 ⇒ 改为 `Yaml_LocalBlock_DiscriminatorOnly`（allow_general:false / 显式 turn_gate|relation_judge|model_path / 绝对 .gguf / 块内无 chat / 权重 >100 MB）。
- **新发现（R464 候选）**：`ServiceCollectionExtensions.cs:300` —— 配置 `model_path` 指向不存在文件时**静默回退默认权重**（首跑 BP 负控因此 VOID）；缺模型虽 fail-open 但净亏 7.1%（重试开销）。
- **证据**：`eval/rover/r463/{verdict-r463.json,run_arm.sh,settle_r463.py,calls-*.jsonl,turns-*.jsonl,deletion-ledger.json}`；`docs/reports/r463-3b-gate-adoption.md`；registry `r463.local-gate-model-switch` / `r463.model-cleanup`。

### R464 (2026-09-15) · 本地判别通道「配置错配」fail-closed（消灭静默回退默认权重）

状态: 已完成 (R464)

- **触发（R463 现场 + 全候选推进令）**：R463 BP 负控首跑 VOID —— 不是负控设计错，而是产品代码静默替换配置意图。缺陷位 `ServiceCollectionExtensions.cs:300`：`lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` 把「配置错配（声明了但文件不存在）」与「配置未声明」塌成同一态，两者都跑内置默认权重。
- **改动**：① 新增 `src/agent.llamacpp/LocalChannelWiring.cs`（三态来源判定：未声明 / 可用 / **错配**）；② `ModelCatalog` 增 `LocalChannelConfig.Declared`（解析 `local:` 段时置位）；③ 接线改为错配 ⇒ **显式告警 + 通道置不可用 + 降级远端**（fail-open 但可见，不再冒名默认权重）；④ `LocalChannelWiringTests` 8 例机检（含源码形状门，禁注释即可满足）。
- **E2E（同网格 p12 / 同桩 / 同 role=`skeptic-growth.rbin` / AOT 0 IL 警告二进制 `/tmp/pub_r464/agenthost`）**：Arole(门关) 21 调用/33,323 tok；**B3B(门开) 8 调用/20,487 tok ⇒ 降幅 38.52%**（≥30% 达标）；BP(cfg 错配而 env 默认存在) 21/33,306 **且本地 eval/gen=0/0、告警 2 条、0 次 Skip**；BP2(cfg+env 双缺) 21/33,311。
- **单一变量分母（事后判据 C10）**：BP 与 B3B 同 role/同 relation_judge/同网格，唯一变量 = 本地通道可用性 ⇒ 降幅 38.49%。
- **零回归物理证据（C8/C8b）**：跨版本逐位相同 —— R463≡R464 的 BP2 `21/33,311`、B3B `8/20,487`；而 R463 BP `8/20,484`（静默跑默认 3B）→ R464 BP `21/33,306`，**负控冒名消失**即修复的物理证据。
- **本地承重（C9）**：门开臂 4 次 `gate:skip→local`，每次本地实算 eval≈342 tok / gen 2 tok ⇒ Skip 不是「空跳过」。
- **判据纪律（C6 FAIL 保留）**：预注册 C6 写成「真缺模型 ⇒ gate_events==0」与产品语义不符（实测 12 条事件全 `Pass` + `gate:degraded:failed_or_empty→remote`）⇒ **C6 保留 FAIL 不改写**，正确形态单列 `checks_posthoc`（C6′ 双绿）。
- **新发现（R465 首要候选）**：门控轮墙钟 **40.7/40.9/70.8/102.2 s**（门开臂总 256.0 s）vs 门关臂 0.04–0.08 s ⇒ token 降 38.5% 换来被门控轮 +40~100 s 延迟（3B CPU、`gpu_layers:0`、每次本地调用含服务启停）。下一轮做长驻/预热 + prompt cache 复用。
- **单测诚实口径修正**：全量 **1387/1388**（此前轮次报的「132/132」是**过滤器跑**，不是全量）；唯一失败 `ExecutorHardeningTests.FileLock_ConcurrentAppend_NoLoss_NoInterleave` 满载 120 段得 119，**单跑 3/3 全绿** ⇒ 列 R465 候选（并发下可证，不用重试掩盖）。形式门禁 60/60 非假绿。
- **证据**：`eval/rover/r464/{verdict-r464.json,run_arm.sh,settle_r464.py,calls-*.jsonl,turns-*.jsonl,host-*.log,prov-*.json}`；`docs/reports/r464-config-fail-closed.md`；registry `r464.local-channel-config-fail-closed`(L2) / `r464.settle-sentinel-and-cross-round-determinism`(L1)。
- **下轮候选（R465）**：① 本地门延迟（长驻/预热 + 缓存复用，目标 ≤10 s/门控轮）；② 真诉求轮可跳性（按需注入压前缀，97% 命中红线）；③ 并发偶发单测；④ 分母口径升级到真实供应商计费面；⑤ 同臂复跑把确定性升为预注册判据；⑥ bge 嵌入器侧同形接线机器核查。

## R465（2026-09-16）真诉求轮可跳面（纯复述族）+ 本地通道预热 + FileLock 释放不 unlink

- **因果链**：R464 已 −38.52%，但 ① `再讲一遍。`/`从头再说。`（t6/t9）是「把上一条答复原样重来」的真诉求却仍走远端主调用（不需要新内容 ⇒ 可直接回放）；② 本地 3B 的装载（实测 **26.0 s**）与 prefill 全落在用户可见门控轮上；③ `FileLock.Release()` 在「关 fd 后按 pid 校验删锁文件」有 unlink 竞态（老持有者持已 unlink inode、新来者持新 inode ⇒ 两个持有者，历史 120 段得 119）。
- **实现**：`TurnGateJudge.IsPureRepeat`（三道：完整复述标记 / 去标点 ≤14 字且字符全属复述白名单 / 无问号）在 `MechanicalPass` **之后**前置判 Skip ⇒ 零 r1 零远端；本地消化 = **回放上一条 Assistant 答复原文**；开关 `AGENTFRAMEWORK_GATE_REPEAT_SKIP`（默认 on，off=R464 行为）；后置否决条件同步加 `¬IsPureRepeat`（漏改会静默失效）。`ILocalGenerationPort.WarmupAsync` + `AGENTFRAMEWORK_LOCAL_WARMUP=1`。`FileLock.Release` 不再 unlink（锁身份=inode），`TryBreakStaleLock`→只读 `IsHolderDead`，`Describe` 优先 `/proc/locks`；bge 嵌入通道改用 `ResolveEmbedder` 三态接线。
- **同网格 5 臂（p12/同桩/同 role/同 AOT 二进制 `e895ae3d…`）**：Arole(门关) **21 调用/33,323 tok**；B3B(复述关) **8/20,487**（逐位复现 R464/R463 ⇒ 零回归）；**R(默认) 6/14,529 = −56.40%**（≥30% 达标），repeat 命中 2、本地 r1 只 4 次（Ack 轮）、复述两轮 `eval/gen=-1`；R2 复跑 Δ+2 tok 已归因（工作区目录名 `run-R` vs `run-R2` +1 char × 2 次调用）；W1 预热首个门控轮 **49.9 → 22.2 s**（`warm_ms=26036`），稳态 19.4 s 不变。
- **延迟归因**：llama-server **常驻**（每臂 2 个 pid：bge + 3B，各 1 个，4 次本地调用无重复装载）⇒ 稳态 19.4 s/轮 = 342 token prefill ≈ **17.6 tok/s**（2 vCPU）= 当前硬件的结构性下界，≤10 s 目标未达。
- **真实计费面（n=6 回放真实端点）**：桩侧估算器**系统性低估 18.1%**（`est/real` 均值 0.8192 ⇒ **k=1.221**）；真实侧出现 prompt cache 命中 640/2,304/2,816 ⇒ 真实成本降幅可能大于 token 降幅（未量化）。
- **锁纪律**：确定性机理复现（删锁文件 ⇒ `both_inside=true`；不删 ⇒ 互斥成立）+ 跨进程真值 G43（子进程持 flock ⇒ 拒锁；退出 ⇒ 内核放锁、接管、锁文件全程保留）+ G44 剥注释结构门；`ExecutorHardeningTests` **10×13 全绿**。
- **诚实边界**：C3 FAIL（t6 用户可见答复被 R458 承接反问覆盖：「本会话还没有产物。继续什么？」⇒ R466 候选①）、C6 FAIL（Δ+2 tok）；两者正确口径单列 `checks_posthoc`（C3p/C6p/C4b2）。全量单测 **1409/1409**；AOT **15,335,040 B** 0 IL。
- **证据**：`eval/rover/r465/{verdict-r465.json,arm-*.json,run_arm.sh,run_all.sh,settle_r465.py,mech_unlink_race.{py,json},real_billing_probe.{py,json}}`；`docs/reports/r465-repeat-skip.md`；registry `r465.pure-repeat-skip`(L2) / `r465.filelock-release-no-unlink`(L2) / `r465.local-channel-warmup`(L1) / `r465.embedder-channel-three-state`(L1)。
- **下轮候选（R466）**：① 承接反问 vs 复述回放优先级（有指代 ⇒ 回放优先）② 真实成本口径（k=1.221 + cache 命中纳入结算）③ 门控轮稳态延迟（参数/门判输入瘦身，禁前缀缓存）④ 复跑口径固化（RUNDIR 名与臂名无关）⑤ 嵌入通道告警真实命中取证。

## R466（2026-09-16）复述回放 vs 承接反问优先级（修 R465 C3 FAIL）+ 结算类口径单源

- **因果链**：R465 的 C3 FAIL —— `再讲一遍。`(t6) 是纯复述轮，skip 层已按 `repeat_verbatim` 逐字回放上一条答复（21 字，零 r1 零远端），但 R458 承接反问**收口面无条件覆盖**，用户可见答复变成 46 字「本会话还没有产物。继续什么？」。根因 = 结算类只在打点处算过一次，收口面不知道本轮已本地确定性结算，于是拿空事实集重算接地性并覆盖。
- **实现（单源 + 可消融）**：① `ContinuationBrief.SettleRepeatVerbatim`（口径唯一字面值）+ `ShouldApplyFallback(settleKind, reply, facts)`；② 主链 skip 支把结算类写入 `_localSettleKind`（打点与收口面同源）+ 逐轮清零；③ 收口面改读该判据；④ 开关 `AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY`（默认 on；置 0 = R465 行为）。
- **同网格 4 臂（p12 / 同桩 / 同 role / 同一 AOT 二进制 `/tmp/pub_r466/agenthost` 0 IL）**：Arole(门关) 13 调用/32,097 tok；**R(默认) 6 调用/14,529 tok = −54.73%**；NC(开关 off，同二进制) 6/14,531 且 **t6 复现 46 字缺陷**（外部真值：`suppressed=false/apply_fallback=true`）；R2 复跑与 R 逐位同（Δ+2 tok = RUNDIR 名 +1 char × 2 次调用）。
- **预注册判据 C1–C6 全绿**，另 posthoc：Δtok（本版 R vs R465-R）= **+0**；机制可证 = 两臂 skip 事件逐位同（同 msg_sha16 / 21 字回放），差异只在收口优先级遥测单源。
- **单测**：全量 **1411/1411**（基线 1409 + 新增 2）；G37 强化「主链禁 `repeat_verbatim` 字面值」+ 新 G40（写入先于消费/开关可见/逐轮清零），负控实测（还原调用点 ⇒ G40 红，源文件 sha256 复原一致）。
- **诚实边界**：Arole 分母跨轮漂移未消除（R465 21/33,323 vs R466 13/32,097），已定位 = 判官路由（R465 8 次 judge 走远端、R466 同 prompt 走本地 ⇒ 0 远端 token），故「Arole 为稳定分母」前提本轮被证伪；两种分母下降幅 56.40%/54.73% 均达标。未做真实流量复验、未测运行期内存。
- **证据**：`eval/rover/r466/{verdict-r466.json,arm-*.json,calls-*.jsonl,turns-*.jsonl,run_arm.sh,settle_r466.py}`；`docs/reports/r466-repeat-priority.md`；registry `r466.repeat-replay-priority`(L2) / `r466.settle-kind-single-source`(L4)。
- **下轮候选（R467）**：① 分母固化（判官强制本地 + 就绪门，消 13↔21 漂移）② 真实流量（state.db 1542 轮）复验 −54.7% 外部效度 ③ 门控轮稳态延迟（17.6 tok/s 下界）④ 真实计费口径（k=1.221 + cache 命中）纳入结算 ⑤ 嵌入通道告警真实命中取证。

## R467（2026-09-16）分母固化：远端调用分解台账 + 臂可比性闸 + 同二进制「判官标志」复现裁决

- **因果链**: R466 诚实边界①（Arole 分母跨轮漂移 21/33,323 ↔ 13/32,097）只给了「判官路由」这个归因，**台账里既没有路由字段、也没有任何机检**。生产代码里唯一产生「真发远端请求的判官」的路径 = `RelationJudgeEnabled != true`（`ModelQueueRouter.cs:330` ⇒ `IndustrialAgentV2.cs:1843`）⇒ 假说 **H1 = 漂移真因是臂脚本 `relation_judge` 标志**（R465 `run_arm.sh:43` RJ=false / R466:39 RJ=true）。后果：同名臂「Arole=稳定分母」可在两轮之间静默失效，KPI 不可比。
- **H1 裁决**（同二进制 / 同桩 / 同网格 p12 / 同 role；单变量 = `relation_judge`）：`Arole`(RJ=on) **13 调用/32,097 tok** 逐位复现 R466；`Aroff`(RJ=off) **21/33,323** 逐位复现 R465；差 **8 次远端调用 / 1,226 tok**，与桩侧这 8 条判官调用实测（prompt 1,170 + completion 56）**逐位吻合** ⇒ H1 证实（非折算、非估计）。
- **分母与 KPI**：生产 config = `turn_gate:true` + `relation_judge:true` ⇒ 生产等价分母 = **13/32,097**；`R` = **6/14,529** ⇒ **−54.73%**（沿用 R465 口径 = 56.40%），两口径均 ≥30%；远端调用 **6 vs 21**（省下的最大单项 = 8 次判官远端调用）。
- **器具（本轮实交付物）**：`settle_r467.py` 增 `calls_class`（桩侧逐条分类 main/judge/micro/other）、`judge_route`（events·local·shortcircuit·remote_real·remote_fallback + ms + prompt_len）、`remote_llm_events`（宿主 `llm_call` 内部计数，与桩侧外部计数互检）、`flags-<ARM>.json`（生成后 config 解析 + env 声明 + 二进制/配置/role sha + 字面 cwd）；`denominator_gate.py` 新闸 **G1 分解恒等式 · G2 内外一致 · G3 路由干净（禁静默远端兜底）· G4 同名臂跨轮标志逐键同（异 ⇒ VOID，异名异类 ⇒ NA 拒绝背书）· G5 声明完备**；`arm_class` 单一来源（settle 直接 import 闸里的 `arm_class_of`）。
- **闸实测**：自检 **3/3**（S1 = 用**真实历史** R465 台账当生产等价分母 ⇒ 判红，差异键恰为 `relation_judge`；S2 = 破坏恒等式 ⇒ 红；S3 = 只改器具 sha ⇒ 绿，不把二进制换代误判成分母漂移）；审计 **X1–X4**: 同名臂跨轮可比 ✅ / 同类分母跨轮异名可比 ✅ / 真实漂移负控判红 ✅。
- **预注册判据 C1–C6 全绿**（C4 = H1 直接判决，精确等值）；`C7` 为**事后增补**（已标注，不作预注册强度）。
- **诚实边界**：① 4 条 `prompt_len=0` 的判官短路（零请求）内部机制未查明，只按可观测口径计数；② 历史重建台账的 `repeat_priority`/`role_sha256` **不可核**（旧脚本未声明），只有 R467 起可核；③ 判官本地化把 8 次调用从 ~42 ms（远端）移到本地，实测 **40.0 → 126.6 s**（R466 实测 58.2 → 144.1 s，时序相关）⇒ **token 收益确定、延迟代价未优化**；④ 本轮**未改 `src/**`** ⇒ 无 AOT/IL 读数，被测二进制 = R466 产物（`sha256=9f5f9e69…`，`role sha=ecb75f53…` 均回算吻合）；⑤ 真实流量（state.db 1542 轮）**未复验**。
- **证据**：`eval/rover/r467/{verdict-r467.json,ledger-*.json,arm-*.json,gate-selftest.json,gate-audit.json,flags-*.json,calls-*.jsonl,turns-*.jsonl,run_arm.sh,settle_r467.py,denominator_gate.py}`；`docs/reports/r467-denominator-pinned.md`；`docs/plans/v0.84.0-r467-denominator-pinning.md`；registry `r467.call-decomposition-ledger`(L2) / `r467.arm-flag-comparability-gate`(L4)。
- **执行证据**：形式门禁 9/9 绿（执行数 9>0）；全量首跑 1410/1411（1 例**既有 flake**：`TelemetryPendingTests` 依赖 `AgentTelemetry` 静态类 pending ring，对执行顺序敏感），该例隔离跑 2/2 绿、全量复跑 **1411/1411** 绿 —— 如实记录，**不以复跑代替修复**。
- **下轮候选（R468）**：① 判官**延迟面**（judge 与门共用常驻端口的合并/优先级；判据 = `local_ms` 首末 + 门控轮稳态延迟，**禁以 token 面代替**）② 真实流量 1542 轮用 `calls_class` 分解复验（判定「守卫承重」承在哪类调用）③ 前缀按需注入（主调用 prompt 逐轮单调增 2,019→3,461 tok = 当前最大单项成本）④ 历史器具键回填 ⑤ `TelemetryPendingTests` 顺序隔离（判据 = 连续 3 次全量 1411/1411）。


## R468（2026-09-16）真实流量组成 vs 网格组成：门判降幅的**外部效度**机检

- **因**: R465/R466 的 −56.40%/−54.73% 分子分母同取一张 12 轮网格（4 认可 + 2 复述 + 6 其他 = **50% 可跳面**）；该组成系为族覆盖而设计，从未机检是否代表真实分布。R449/R452 的「真实 ack = 0/1542」是**旧规则**结论，未在新规则（Ack 主闸 + 纯复述直跳 + MechanicalPass 优先）上复验。
- **法**: `eval/rover/r468/gate_rules.py` 从 `LocalGenerationPort.cs` **正则派生**规则（`:304`/`:356`/`:359`/`:458`/`:461`/`:469`/`:477`，记源 sha256），期望值取产品自身 `InlineData`（认可族 13 / 纯复述族 15）⇒ `--selftest` PASS；新测试 `GateRulesPortDiffTests`（3 例）在 **423 行**语料（真实轮 + 网格 p12 + InlineData）上断言端口标签 ≡ 产品三判组合。
- **读数（机检）**: 真实语料 = `state.db` `role='user'` 2,585 行 − 1,406 系统注入 = **1,179 真实轮**；`pass 890 (75.5%) / other 173 (14.7%) / driver 116 (9.8%) / ack 0 / repeat 0` ⇒ **机械可跳面 0.00%**，需远端主调用 **90.2%**。对照网格 **50.0%** 可跳。
- **结论**: 「≥30% 降幅」绑定**具备可跳结构的语料**，在唯一可得的外部真值通道上出现率 0 ⇒ 不外推真实用户面；真实分布 90.2% 轮必走远端 ⇒ 撬动真实 KPI 的杠杆是**单次调用 token 量**（前缀按需注入/缓存命中），列为 R469 首选。
- **负控**: 注入「好的，明白。」/「再讲一遍。」⇒ `skip_face=2`（指标非恒 0）；产品侧存在性断言「真实行可跳面 == 0」存在即 FAIL。
- **形式校验**: 全量单测 **×3 顺序隔离连续 1414/1414**（`Failed 0` ×3，执行数一致）；定向差分 3/3；零产品行为改动、零 llama-server、零远端、未 push。
- **边界**: 判据落盘晚于探索性首跑（C1–C6 为复现跑，首跑读数单列 posthoc）；端口 ≡ 产品仅覆盖 423 行；「系统注入剔除」前缀规则本身未机检；真实语料 ≠ 产品最终用户分布（待确认）。

## R469（2026-09-16）命中率理论上限分档：用户轮长度不可压

**因果链**：R461 起 97% 命中率以单值红线报出（前缀 3.1k ⇒ 新增 ≤93.5 tok），从未检验「新增里的用户轮能否被注入策略压到 93.5 tok 以下」→ 用桩侧落盘的全量 `messages[]`（外部真值）离线复算逐对公共前缀 + 按用户轮长度分档 → 新增部分 = 上一轮承接（15/21 字符）+ **本轮用户轮（206–367 字符）**，由用户轮主导，注入侧无可压空间。

**读数**

| 档（字符） | 轮数 | 占比 | 中位用户 tok | 前缀 2.1k | 前缀 3k | 前缀 4k | 97% 可达 |
|---|---|---|---|---|---|---|---|
| 0–30 | 130 | 32.5% | 11 | 98.51% | 98.94% | 99.21% | ✔ |
| 31–93 | 68 | 17.0% | 51 | 96.70% | 97.66% | 98.23% | ✔ |
| 94–200 | 64 | 16.0% | 138 | 92.99% | 94.97% | 96.18% | ✘ |
| 201+ | 138 | 34.5% | 300 | 86.80% | 90.33% | 92.57% | ✘ |

门控臂 R 主调用 **5/5 对逐字节 tail-only**（`prefix_share`=1.0）⇒ 可缓存性经实测，非假设；负控（system 首段动态字段）`share` 1.0 → 0.7918 ⇒ 指标非恒真。

**结论**：命中率须**分档报**（上限 + 达成轮占比）：短档 49.5% 现况即 ≥96.7%；长档上限 ≤96.2%，97% 结构性不可达。提升路径由「压新增」改为「升前缀」（稳定内容前置、缓存摊薄），与 R461 按需注入方向相反 ⇒ 列 R470。

## R470（2026-09-16）真实流量命中归因通道：K2b 在真实流量上 100% 不适用

**外部真值**（`data/telemetry/host.jsonl`，真实远端调用 43 条，`sha256=2a9e3449…9a13`）：`effective_hit_rate` **43/43 = -1**（同会话前驱 0）⇒ 既有首要 KPI 对真实流量**结构性不可测**；而供应商侧命中客观存在：hit>0 **32/43（74.4%）**，命中量饱和 **2,048~2,304**（64 对齐，例外 2 条 `hit=127` 逐条列出未静默过滤）。

| 通道 | 调用数 | 命中 > 0 | 命中占比 |
|---|---|---|---|
| shared_prefix（无同会话前驱） | 43 | 32 | 45.44%（hit 59,518 / prompt 130,974） |
| same_session | 0 | — | 无样本 |

分档新算量（真实调用）：`<400` 档 230 tok（命中 0）／`2.9k~3.1k` 档 **1,020**（命中 66.75%）／`5.2k~6.4k` 档 **3,320**（命中 39.15%）⇒ 共享前缀（≈2k）不随 prompt 增长，**C 档每次调用 3.3k tok 新算**才是 KPI 分子主来源。

**改动（只增不改）**：`PromptCacheKpi` 新增 `cache_channel`/`shared_prefix_hit_tokens`/`shared_prefix_hit_rate`（无前驱归因共享前缀；有前驱一律 -1，**禁双计**；未上报 -1 不得冒充 0），三处 data-carrying `llm_call` 全铺；97% 红线与 `effective_hit_rate` 语义**一字未动**。AOT 重发布 `agenthost` **15,343,232 B**、**IL 警告 0**；`dotnet test` **29/29**（含形式门禁 9/9）；`real_calls.py` 判据 C1~C6 **全绿**。

**诚实边界**：未发起真机调用（配额）⇒ 样本仅 43 条且全为会话首调用；`shared_prefix` 因果（跨会话复用 vs 同文本缓存）不可分；**命中是否在计费上打折未取到** ⇒「命中⇒省钱」仍是未验证前提。

**下轮候选**：① `scripts/kpi_cache_hit.py` 纳入新通道聚合（否则新字段落盘无人聚合 = 空心）；② C 档 3,320 tok 新算的组成分解（共享 2.1k + 私有 3.3k），把「升前缀」可执行化；③ 红线迁移为「分档上限 + 达成轮占比 + 分通道」。

## R471（2026-09-16）分通道聚合：真实流**实发 0/43** ⇒ R470 的 43 是派生值

**外部真值**（`data/telemetry/host.jsonl`，sha256 `2a9e3449…9a13`，`llm_call` 43 条）：含 `cache_channel` 字段者 **0 条（0/43）** ⇒ R470 的「shared_prefix 100%（43/43）」是**证据脚本派生值**，产品遥测侧无物可读。聚合器此前不认识这些字段 ⇒ 任何后续聚合都会把**派生量当实发量**读走（空心 + 不可外部复核）。

**改动（只增不改，`scripts/kpi_cache_hit.py` sha256 `0025d67c…3f18`，307 行）**：新增 `CHANNELS`(:63) / `chan_of`(:66，`PromptCacheKpi.Channel` 逐字移植) / `aggregate_channels`(:71-166)；打印段(:236-254) 与 JSON 键 `channels`/`channel_verdict`(:268-269)；退出码 `1` 亦含分通道判红。**fail-closed 语义**：缺字段 ⇒ `unreported.absent_field`（**既不算 0 也不算 `shared_prefix`**）；非 `shared_prefix` 通道两字段须显式 -1（≥0 ⇒ `double_count` 判红，缺失 ⇒ `wiring_hole` 判红）；`shared_prefix` 内 `hit=-1` ⇒ 入 `hit_na` 不进求和（「0 命中」与「未上报」可分）；守恒式 `emitted.rows+unreported.total==calls` 不闭合即判红。`effective_hit_rate`/`cacheable_tokens`/97% 红线**一字未动**。

**读数**：`check_channels_r471.py` **C1~C6 全绿 6/6，rc=0** + **C7（形式门禁）全绿**（`dotnet test` **27/27**，failed 0/skipped 0/exit 0/执行数>0，读数自 `eval/rover/r471/formgate-r471.log` 机检取值）⇒ **合计 7/7 PASS** —— 实发 `emitted.rows=0`／`absent_field=43`／**`emitted.shared_prefix=0`（≠43）**；对照列 `derived.shared_prefix=43`、派生命中 **59,518**（=R470 值），守恒 `0+43==43 ✓`；**正控**同形夹具 5 行精确读回（`{shared_prefix:2, same_session:2, unknown:1}`，命中求和 2,048，已上报 1/未上报 1，`emitted.rows=5>0` 非空跑）；**负控 6/6**（双计判红／未上报不入和／`unknown`／缺字段不冒充／归因反写有判别力／接线洞判红）；**零回归**：legacy 键与 `HEAD` 版脚本逐键相同，新增键仅 `channels`/`channel_verdict`。形式门禁 `dotnet test` **27/27**（含 `PromptCacheRedlineTests` 对脚本的逐串锁 `REDLINE = 0.97` 仍绿）。

**诚实边界**：本轮**无 C# 改动** ⇒ 按铁律**不触发** AOT 重发布（体积沿用 R470 `agenthost` 15,343,232 B）——是「不触发」不是「未测到」。**实发面在真实流上零样本**（43 条全部早于 R470 接线）⇒ 实发正确性由同形夹具 + 负控背书，**不由真实流量背书**；真实流只能证明「聚合器不再把派生量冒充实发量」。未做真机调用；不改链/不改红线 ⇒ 本轮无 KPI 数值变化，只产生**可复核性**。

**下轮候选**：① C 档 3,320 tok 新算的组成分解（共享 ≈2.1k 不随 prompt 增长 + 私有），把「升前缀」可执行化；② 红线迁移为「分档上限 + 达成轮占比 + 分通道」联合判据；③ **实发字段的真实样本**（当前 0 样本是本轮最大未覆盖面）。

## R472（2026-09-16）前提裁决：远端命中「饱和」**不是**供应商上限（真机受控实验，NO_CAP）

**外部真值**（8 次真实调用，`deepseek-flash` ≡ `config/base/models.yaml:9,16` 生产模型/端点，逐调用原始 `usage` 落 `eval/rover/r472/real-usage-r472.jsonl`）：共享前缀阶梯 910 / 3,789 / 5,811 tok ⇒ warm 命中 **768 / 3,584 / 5,632**（hit/前缀 0.844/0.946/0.969 单调升，且全部为 64 整数倍），**观察最大值 5,632 > 假设饱和上沿 2,304** ⇒ R469/R470/R471 共同依赖的「provider 在 ~2.1k 处截断命中」被**单条观察直接证伪**。三条 cold（唯一 nonce 开头）命中 **0/0/0**（负控）；恒等式 `prompt==hit+miss` **8/8**；复现臂 5,632==5,632。成本 32,643+128 tok = **0.008954 CNY**（预注册上限 0.02 CNY）。

**机制定律**（事后派生，5/5 点吻合）：`prompt_cache_hit_tokens == 64 × ⌊(prompt_tokens − 142) / 64⌋`，尾部常数 **c=142 由 5 点不等式交集唯一确定**（c=141 被 MID 臂排除）⇒ 命中量只由「与历史调用共享的前缀长度」决定，块对齐 **64 tok**。

**读数**：`probe_cache_cap.py` **C1~C6 全绿 6/6**，**C7（判定函数自检）FAIL**（原判保留、不覆盖，按判据纪律走事后路径）⇒ 首轮 6/7；`check_criteria_r472.py`（**新 API 调用 0 次**）事后判据 **P0~P4 全绿 4/4**：P0 数据级证伪（不依赖判定函数）／P1 定位 C7 根因（v1 的 CAP 分支需 `P_MID ≥ 3,150` 才可达，与臂尺寸不自洽）／P3 修正版 v2 自检 4/4 且真实数据 v1=v2=**NO_CAP** ⇒ **结论不依赖判据修正**／P4 机制定律 5/5。形式门禁 `dotnet test` **27/27**（failed 0/skipped 0/exit 0/执行数>0，读数自 `eval/rover/r472/formgate-r472.log` 机检取值）。

**口径后果**：真实流 43 条（hit 19×2,048／7×2,176／2×2,304／2×256／2×127／11×0；prompt 229–6,360，中位 3,064；R470 已证 43/43 **无同会话前驱**）的「饱和」= **共享脚手架 ≈2.1k（推断）+ 各会话私有任务文本 1.0–3.5k**，不是 provider 能力上限 ⇒ R469「97% 红线对长档结构性不可达」的**机制表述作废**（成因是「无前驱首调」的采样面）；多轮会话命中 ≈ 前一轮 prompt 长度 ⇒ 命中率随轮次单调上升。**升前缀有效，但只在把「新算」变「复用」时才有效**。

**诚实边界**：本轮**无 C# 改动** ⇒ 按铁律**不触发** AOT 重发布（体积沿用 R470 `agenthost` 15,343,232 B）——是「不触发」不是「未测到」。合成 filler ≠ 产品提示词 ⇒ 证明的是**供应商机制**，**不是**产品链的真实命中（产品链实发样本仍 **0**，R471 记录）。未测：命中/未命中的**计价差**（只测 token 计数）、其它 provider/模型、以及「脚手架 ≈2.1k」的直接测量（需实发 prompt 文本，当前 0 样本 ⇒ 标「待确认」）。

**下轮候选**：① 真机多轮会话（同会话 ≥5 轮）实测 `hit_n ≈ prompt_{n-1}` 与每轮新算占比 ⇒ 直接给出用户 KPI（一轮任务 token）的分母分解，并把红线重述为「首调 vs 多轮」分档判据；② 产品链**实发样本**（仍 0 样本）并用机制定律锁 `hit == 64×⌊(可复用前缀−c)/64⌋`；③ 私有增量压缩（按需注入）A/B 对 miss tokens。

**台账/索引（R472 附）**：`docs/reports/iteration-master-plan.md` 的「轮次索引」由 R441–R458 扩展为 **R441–R472**（+27 行，`eval/rover/r472/refresh_master_index_r472.py` 机取自 registry；**幂等重跑 `rows_added=0`**），覆盖自检行改为机派生：`轮号 [441…458, 460…472]；registry rows=129，updated_round=R472`，并显式标出 **459 号未被使用**（registry 无行、improvements.md 亦无块）。registry 追加 2 行（`r472.prefix-cache-no-provider-cap` L3 / `r472.criteria-posthoc-and-mechanism-law` L2），`git diff --numstat` = **+32/−1 行**（IO 保形，非整档重写）。

## R474（2026-09-16）KPI 分母升级：桩估算 → **供应商 usage 真值**（真端点双臂，首次拿到产品链实发缓存样本）

**外部真值**（`eval/rover/r474/usage-*.jsonl`，中继 `relay_real.py` 捕获的供应商 `usage`，非派生）：同一 AOT 二进制 / 同一 p12 网格 12 轮 / 同一 role 夹具，唯一变量 = 门控标志。

| 臂 | 轮 | 中继调用 | prompt | hit | miss | completion | total | 命中占比 | 成本上界 |
|---|---|---|---|---|---|---|---|---|---|
| Arole 门关 | 12/12 | 20 | 70,890 | 61,952 | 8,938 | 5,204 | **76,094** | 87.4% | 0.024865 CNY |
| R 门开 | 12/12 | 9 | 29,477 | 22,912 | 6,565 | 3,292 | **32,769** | 77.7% | 0.011580 CNY |

**读数**：**总 token 降幅 56.94% / 远端调用次数降幅 55.0% / prompt 降幅 58.42%**（预注册判据 ≥30% ⇒ C5 PASS）；恒等式 `prompt==hit+miss` **20/20 与 9/9 全成立**；预算闸 0.036445 ≤ 0.15 CNY、blocked=0、负控（cap=0 → 402 零外发）PASS。**分母对照**：桩口径（字符/2）Arole 53,565 → 供应商 70,890 = **1.323×**，R 21,026 → 29,477 = **1.402×** ⇒ 桩口径系统性低估 24–29%，但降幅在两种分母下同向同量级（桩口径 R467 **−54.74%** vs 真值 R474 **−56.94%**，差 2.2pp）⇒ R465–R467 的结论**不是分母假象**，绝对读数此后以供应商 usage 为准。**缓存真值首批**：逐主调用 hit_rate 0.894–0.952；`Pearson(lcp_est_tokens, 供应商 hit)=0.8175(Arole)/0.7593(R)` ⇒ R472 机制定律首次在**真实链路**上得到同向强相关印证；`effective_hit_rate` 首次可算 11/16 与 5/6，其中 **3 例 >1.0（1.0589/1.0066/1.0822）** ⇒ 该指标分母取「上一条 prompt」的口径缺陷（命中可超上一条全量）。

**判据**：C1/C3/C4/C5/C6/C7/C9/C10 PASS；**C2（relay == host `llm_call`）字面 FAIL 保留不覆盖**（Arole 20 vs 16、R 9 vs 6），事后归因 P1：`llm_call + llm_call_recover` 恒等成立（20=16+4、9=6+3）⇒ 每条远端调用都有遥测点，但 **recover 行缺 prompt/缓存字段 ⇒ 产品自记账漏 15,458 prompt tokens = Arole prompt 总量的 21.8%**（R 臂 34.5%）；P2 扣除 recover 同类比较 −62.1% ⇒ 降幅不靠重试差异解释。

**诚实边界（本轮 KPI 达标，质量判据不达标）**：真端点首次把**回复正文**暴露出来 —— R 臂 12 轮里 **6 轮模板应答**（`收到，继续按当前方向推进，本轮不重新规划。`）+ **3 轮用户可见「模型未产出正文…请重试」横幅**（t1/t7/t8），仅 3 轮（t10–t12）为实质回答；同轮 Arole 12/12 全实质。`llm_call_recover` 双态：Arole **4/4 recovered=true**，R **0/3 recovered=false**（retry_len=0）。可用性缺陷（非设计预期）：t6「再讲一遍。」与 t9「从头再说。」被判 `mechanical:repeat→local` 回模板 ⇒ 重复类指令必须**回放上一条正文**（零 token）而非模板。归因边界：空正文是**供应商侧**失败模式（两臂均出现首次空正文），本轮 3 例重试全败 vs Arole 4 例全成，n=3/4 **不足以**断言与门控相关；器具未落盘采样参数与 `finish_reason` ⇒ 根因**未定位**（下轮补）。**无 C# 改动 ⇒ 按铁律不触发 AOT 重发布**（体积沿用 `agenthost` 15,343,232 B）；未测：命中/未命中的计价差、其它 provider、recover 通道的兜底模型。

**下轮候选**：① **repeat-skip 回放上一条正文**（修 t6/t9 质量 + 省 token，改链 ⇒ 需 AOT 重发布 + IL 警告 0）；② **recover 通道加固**（空正文失败时降采样/换非推理模型兜底 + 给 recover 行补 prompt/cache 字段，补 21.8% 漏账）；③ `effective_hit_rate` 口径修正（`hit/min(prompt, cacheable)`）并回归红线 97%；④ 中继器具补采样参数/`finish_reason`/响应尾部落盘以定位空正文根因；⑤ `kpi.jsonl` 接入供应商 usage 真值列（与产品 `llm_call` 双列并行，禁混算）。

**台账/索引（R474 附）**：`eval/rover/r474/refresh_master_index_r474.py`（由 r472 版机派生，`FROM,TO=459,474`）把「轮次索引」表扩到 **R441–R474**（`rows_added=3`，幂等重跑 0）；registry 追加 3 行（`r474.provider-truth-denominator-arms` L3 / `r474.relay-instrument-and-budget-guard` L4 / `r474.quality-regression-evidence` L2），`git diff --numstat` = **+86/−1**（IO 保形）。覆盖自检把 **473** 列为「无登记行」——属实：R473 为审计轮（只补 85 行 `evidence_generated_with`），无 id 行、无 improvements 块。

## R475（2026-09-16）复述回放取实质答复 + 命中率口径禁 >1 + 记账面补齐

**因果链**：R474 首次让真端点回话，暴露两件事：① **质量缺陷** —— R 臂 12 轮里 6 轮模板应答、3 轮用户可见「模型未产出正文…」徽标，实质回答仅 3/12（同轮 Arole 12/12 实质）；② **记账缺口** —— 产品 `llm_call` 自报 16 调用 / 55,432 prompt tokens，而供应商 usage 是 20 调用 / 70,890 tokens，差的 15,458（21.8%）全在 `llm_call_recover` 行（不带 prompt/缓存字段）。同时 R474 报告里 `effective_hit_rate` 出现 **3 例 >1**（1.0589 / 1.0066 / 1.0822），因为「同会话可缓存上界 = min(prompt, 上一条 prompt)」小于真实命中量（命中来自更长的共享前缀）。

**改动（单源 + 可机检）**
1. **回放守卫** `ModelQueueRouter.IsReplayableReply`：空/空白/`LocalSkipFallback` 模板/空正文徽标前缀 ⇒ 不可回放；纯复述轮取不到可回放答复 ⇒ **撤销 Skip 降级远端**（`gate:repeat_no_replayable_prev`），遥测 `repeat_degrade_remote` + `prefilter_repeat_degrade`。徽标文本改由 `EmptyBodyBannerPrefix` 单源常量拼出（判据作用于 Assistant 侧历史文本，非新增用户轮关键词表）。
2. **记账补齐**：`llm_call_recover` 两条 emit（成功/异常路径）补 `prompt_tokens` + `cache_hit_tokens/cache_miss_tokens/cache_hit_rate`（同源 `first`，未上报 -1）。
3. **口径禁 >1**：`EffectiveHitRate` 加 `hit > cacheable ⇒ -1` 钳制；`Channel/SharedPrefix*` 增加 `ExceedsSameSession` 判据（命中量超过同会话上界 ⇒ 归 `shared_prefix`）。
4. **器具**：中继 v2（`relay_real_r475.py`，另存不改 R474 器具 = 证据↔器具绑定）补采样面 + `finish_reason/content_len/reasoning_len/reasoning_tokens/empty_body` + **逐调用**恒等式；`join_usage_truth.py` 双列并账（真值列/自记列硬分离，唯一跨列运算 gap.*，缺字段 ⇒ unreconciled 禁按 0）。

**读数**
| 项 | 值 |
|---|---|
| R474 质量缺陷（R 臂） | 实质 3/12 · 模板 6/12 · 可见徽标 3/12 |
| R474 漏账（Arole / R） | 15,458 tok (21.8%) / 9,171 tok (31.1%) |
| `effective_hit_rate` >1 | 3 例 ⇒ 本轮口径后不再可能（-1 + 归 shared_prefix） |
| 中继 v2 自检 | S1–S7 **7/7**（零真实调用） |
| 并账自检 | PC + NC1–NC4 **5/5**（真数据必有红 ⇒ 判据非恒绿） |
| AOT | 15,343,232 B · sha16 `b03ee2bbb015e972` · IL 警告 0 · V0 rc=0 |
| 定向单测 | R475AccountingTests **8/8** |

**诚实边界**：零真实调用 ∧ 无 llama-server（MemAvailable 1984MB < 2650MB 闸）⇒ 质量修复**未做真机 E2E**；recover 字段闭合在真实流量上未验；命中折价未取到；R474 空正文根因仍未定（本轮只把定因所需证据面补上）。

## R477（2026-09-16）真机 E2E：R475 复述回放守卫**复演达标** + R476 分档打点实发核验 + KPI 降幅复测（−48.75%）

**因果链**：R474 暴露「复述轮回模板」质量缺陷 → R475 改回放守卫（取最近**可回放**答复，否则撤 Skip 降级远端）但只有单测证据、R476 改分档打点也无真机证据 → R477 两轮修复一起上真机：Arole（门关）/R（门开）各 12 轮真调供应商，中继 v2 采 `finish_reason/empty_body` 定因。

**读数（供应商 usage 真值，同夹具 p12 / 同二进制 `db187e0eae7f26ea` / 唯一变量=门控）**

| 臂 | 轮 | 中继调用 | prompt | completion | total | 成本上界 | 命中 token |
|---|---|---|---|---|---|---|---|
| Arole 门关 | 12/12 | 21 | 68,329 | 5,320 | **73,649** | 0.024301 | 58,624 |
| R 门开 | 12/12 | 10 | 35,600 | 2,144 | **37,744** | 0.011970 | 28,160 |

**KPI**：总 token **−48.75%**（预注册 ≥30% ⇒ C2 PASS）· 远端调用 **−52.4%**（21→10）· prompt −47.9% · completion −59.7%；`prompt==hit+miss` 21/21 与 10/10 恒等；预算闸 0.036271 ≤ 0.15 CNY、blocked=0。对标 R474（−56.94%/20→9）为**同向同量级**（非同分布复现，见边界）。

**质量（用户可见）**：R 臂复述轮 t6「再讲一遍。」/ t9「从头再说。」用户可见 = **前序实质答案逐字回放**（298 字符，零远端），回放事件按输入指纹对齐（`local_gate_skip_reply.msg_sha16 == LocalInputFingerprint.Sha16(该轮用户消息)`，kind=`repeat_verbatim`）；确认轮 t2–t5 仍为模板（kind=`template`，未被误升级）；R 实质 6/12。**预注册 C3/C4 字面 FAIL 保留不覆盖**：假设「无前驱 ⇒ 必现 `repeat_degrade_remote`」「t9==t8」被证伪 —— 守卫会**回溯到最近可回放者**（t2–t5 模板与 t8 徽标均不可回放 ⇒ 回放对象是 t1），事后判据 P1/P2/P3 单列 PASS，P4 记录遥测 `turn` 归属越窗 5 条（偏移 0.07–3.4s，无因果序）。

**定因（本轮最重要的负面面）**：20/20 空正文调用的供应商侧 `finish_reason == tool_calls`（请求带 4 个 tools）、`max_tokens == None`（**非**截断）、`reasoning_tokens_max` 仅 395/122 ⇒ 徽标文案「推理过程占满输出预算」是**误诊**；对照 = R474 Arole 请求体逐字段同源而当时 0 徽标 ⇒ **上游行为漂移**（R477 Arole 可见徽标 7/12，不是本轮零改动引入，也不是门控引入）。

**R476 分档打点实发**：真机主调用遥测行 7 字段齐全（Arole 13/13、R 7/7），取值域合法；记录在案：预注册名 `cache_growth`/`cache_band_target` vs 源码 `cache_band_growth`/`cache_target` ⇒ 器具按**源码派生**判定（取不到即 `MISS(src-const)`），漂移单列。

**器具缺陷（本轮发现并修）**：① 臂收口 `pkill -P $HOST_PID` 未收干净本地 r1（`llama-server` RSS 1.83GB 尚在释放）⇒ R 臂起手闸**假阴性**（`MemAvailable=1318MB < 2650MB`，rc=10），12s 后同内存自行回落 ⇒ 新增「沉降等待」+ R451 先例跑前清理（MSBuild 复用节点/空闲 LSP，2634→2792MB）。

**诚实边界**：单夹具单次；上游漂移 ⇒ Arole 非干净基线，−48.75% 只与 R474 的 −56.94% 同向同量级；r1 只覆盖确认轮+复述轮，**未测**「本地生成替代远端实质回答」的增益；C3/C4 预注册原文判 fail（不收窄覆盖）；本轮零 C# 改动 ⇒ 未重发布 AOT（15,355,520 B / `db187e0eae7f26ea` 沿用 R476，未取新证据）；表单门禁 `VerificationFormTests` 7/7（registry 139→**143** 行，4 行 R477 均 L3 + `evidence_generated_with` 冻结 pin `e55aa0c08189`/器具 `47d3280a39f4`）。

**下轮候选**：① 修空正文**误诊文案** + tool_calls 空正文处理（当前最大用户可见质量损失）；② `llm_call.turn` 归属因果化（绑 reply 请求 id，替计数器）；③ 命中率按分档口径重估（R 0.791 < Arole 0.858）；④ 门控扩到低风险实质轮，测本地替代生成的边际降幅（带质量对照）。

**台账（R477 附）**：registry +4 行（`r477.replay-guard-real-e2e` / `r477.kpi-drop-real-endpoint-arms` / `r477.band-fields-live` / `r477.empty-body-root-cause`，均 L3），`updated_round=R477`；注：improvements.md 节序在 R475 后**缺 R476 块**（R476 只落 report + registry，属既有缺口，本文不改写历史）。节内新增器具 `eval/rover/r477/{run_arm_real_r477.sh,run_arm_R_only.sh,check_r477.py}` 与判据 `verdict-r477.json`。

## R478（2026-09-16）空正文定因机制化（finish_reason 判据）+ 请求-轮次因果绑定 + 命中率冷/稳态分列

**因果链**：R477 真机复演抓到两处同源缺陷。① **误诊**：20/20 条「用户可见空正文」调用的上游 `finish_reason == tool_calls`（`max_tokens == None`、`reasoning_tokens` 395/122 ≪ 预算）⇒ 不是预算被推理吃满，而是上游在请求执行工具动作；产品徽标却写「推理过程占满了输出预算」，并据此**白跑一次 32k 预算的重试**（调用数与 token 双浪费）。② **归属漂移**：5 条 `llm_call` 落在所记轮次窗口之外 ⇒ 轮次归属只能靠时间窗猜。③ **读数伪影**：R 臂命中率 0.791 < Arole 0.858 看似机制退化，按 R456b 分列后 **稳态两臂近等（0.9149 vs 0.9190，−0.41pp）**，聚合差 −6.70pp 中 −6.29pp 系**冷启动窗口占比差**（9.5% vs 20.0%）。

**改动（单源 + 可机检）**
1. **定因机制** `src/agent.modelqueue/EmptyBodyDiagnosis.cs`：`EmptyBodyCause{ToolCall,LengthExhausted,UpstreamStop,Unknown}`；判据**只取上游协议字段**（`finish_reason` / `tool_calls` / reasoning 长度），**零用户文本关键词**；文案单源 `Banner(cause, finishReason)`（**产品面仅 3 个调用点**：`ActionLoop.cs:243`、`ModelQueueRouter.cs:736`（空正文）、`:1217`（恢复通告））。
2. **不浪费重试**：`ToolCall` 因 `Retryable=false` ⇒ 空正文分支 `retry_skipped=true`（×2 emit 路径），恢复路径被 `LengthExhausted ∨ reasoning 非空` 守卫。
3. **因果绑定**：`QueueResponse.RequestId`（单调签发）→ `llm_call` 遥测带 `request_id`/`finish_reason`/`tool_calls_n`/`empty_cause` → 透传 `llmResponse.ResponseId` → 链侧 `_replyRequestId` 捕获并逐轮清零、`loop_turn` 打点带 `request_id` ⇒ 轮次归属可按 id **严格 join**。
4. **动作环出口可见**：出口空正文 ⇒ 单源文案 + `ContentIsUserFacing = true`，**禁静默空回复**。
5. **器具**：`eval/rover/r478/check_r478.py`（C1–C7 + 负控 NC1–NC3，fail-closed：取不到源码常量即抛 MISS）、`band_reestimate_r477.py`（R456b 冷/稳态分列）。
6. **台账机派生刷新**：`bind_evidence.py --apply --round R478`（附带抓到本方 3 行缺 `owner_round` ⇒ 形式门禁判红 ⇒ 已补）。

**读数**
| 项 | 值 |
|---|---|
| 定因面机检 | `verdict=PASS 7/7` + 负控 `NC 3/3`（NC1 旧文案⇒C2 红 / NC2 关键词分类器⇒C1 红 / NC3 未透传⇒C4 红） |
| 全量单测 | **1469/1469 ×3**（R476 时 1451 ⇒ 净增 18；Failed 0） |
| 焦点单测 | 30/30 → 43/43 |
| AOT | 15,363,712 B · sha16 `499a7552897992f1` · IL 0 · `env -i --version` rc=0 |
| 命中率（供应商真值） | 稳态 Arole `0.919019`(19 调用) vs R `0.914939`(8 调用) = **−0.41pp**；聚合 `0.857967` vs `0.791011` = −6.70pp（−6.29pp 系冷启动占比伪影） |
| 恒等式 | `hit + miss == prompt` 逐行成立 21/21 + 10/10 |

**诚实边界**：起手闸 `MemAvailable 2293 MB < 2650 MB` ⇒ **本轮无真机 E2E**；`request_id` 因果绑定只证机制存在（真机 join 未验）；分档轴 `prompt_tokens` 代理全落 `201+` 档 ⇒ `band_degenerate=true`，**不冒充分档结论**；预注册晚于焦点单测首跑 ⇒ 描述性数字入 `checks_posthoc`（承 R453）。

## R482（2026-09-16）真机双臂：R478 修复上真链 + 主 KPI 首次达线（−32.21%）+ 模板兜底的质量代价

**因果链**：R478 的「tool_calls ⇒ Retryable=false ⇒ 不重试」只在单测面验过；R413 验收②「一轮 token −30%」从未在真上游同轮双臂达线。R482 把两者一起上真链（同网格 `p12` + 同夹具 `skeptic-growth.rbin` + 同二进制 `6a9b7aed22a22f48`，唯一变量=门控）。

**读数（供应商 usage，逐调用落盘）**

| 臂 | 远端调用 | prompt | completion | total | 轮 | 遥测 |
|---|---|---|---|---|---|---|
| Arole（门控关） | 21 | 68083 | 4551 | **72634** | ok 12/12 | events 37 · blocked 0 |
| R（r1 在管道内） | 14 | 44444 | 4793 | **49237** | ok 12/12 | events 37 · blocked 0 |

**主 KPI**：`(72634−49237)/72634 = **32.21%** ≥30%` ⇒ **R413 验收② 真上游同轮首次达线**；调用 −7 ⇒ 验收③ 可测增益成立。恒等式 `hit+miss==prompt` 逐行 21/21 + 14/14。

**判据（`eval/rover/r482/prereg_r482.json`，先于首跑落盘；prereg 原文）**：H1 **PASS** · H2 **PASS**（Δ7）· **H3 FAIL**（`A.calls=21` 未 <21 ⇒ 按 prereg `fail_action` 记「修复在真链上无可测效果」并单列，不重跑凑数）· **H4 FAIL**（`R.calls=14 >` R477 的 10，跨二进制参考列）· H5 **PASS** · H6 **PASS**（逐字回放 `t6←t1`(434B)、`t9←t8`(606B)；旧误诊文案 0 次）。`verdict_all_pass=False`。

**H3 成因（post-hoc）**：`llm_call_empty_body` 行 `retry_skipped=True` 逐行成立、`empty_cause='tool_call'` 与上游 `finish_reason='tool_calls'` 4/4 对齐 ⇒ 修复**在位**；但空正文基数 **15（R477）→4（R482）** ⇒ 可省调用被上游漂移抽空。**结论收窄**：只证机制在位，不证调用数收益。

**诚实边界**：−32.21% 中 R 臂 `t2–t5` 答复为**同一条 21B 模板**（Arole 同轮 4 条各不相同）⇒ 实质答复轮 **R 6 < A 12**（`checks_posthoc.quality_verdict_H6c_strict_variant`），即降幅一部分来自**模板兜底**而非「本地 r1 生成替代远端」⇒ **R483 第一顺位**；单夹具单次无置信区间；上游可漂移（本轮实测）；本轮无 C# 改动 ⇒ 不重发布 AOT、不冒充新 AOT 证据；未 push（`PUSH_PAUSED`）。

**起手闸归因修正**：R 臂首跑 `MemAvailable=2590 < 2650` 被闸（同 R477 的 llama-server 未释放）；加沉降等待仍红且 `pgrep llama-server=0` ⇒ 真因 = 本方 `dotnet test` 遗留 `VBCSCompiler`（RSS 206MB）；`$HOME/.dotnet/dotnet build-server shutdown` ⇒ `2730MB` 通过、R 臂 EXIT=0。**占用源不止 llama-server，含本方编译服务器**。

**器具**：`eval/rover/r482/{prereg_r482.json,run_both_r482.sh,run_arm_R_only_r482.sh,check_r482.py,verdict-r482.json}`（判据器常量全源码派生、取不到抛 MISS）；本轮 3 条实现偏离/归因修正已留痕 `verdict-r482.json.drift_notes`。登记行刷新（registry +`r482.*` 行）**未做**，列下轮候选。

## R482-Q（2026-09-16）本侧独立复核 R482 + 常量兜底归属与质量面量化

**立场**：只读既有真机产物（`eval/rover/r482/{usage,turns}-{Arole,R}.jsonl`），**不重跑真链、不改 R482 判据 H1–H6**。预注册 `eval/rover/r482/prereg_quality_face.json`（先于首跑）；器具 `eval/rover/r482/quality_face_probe.py`（常量由 `src/agent.modelqueue/ModelQueueRouter.cs` 正则派生，取不到 ⇒ `rc=3` 弃权）。

- **主 KPI 独立复算**：调用 **21 / 14**、total **72,634 / 49,237**、降幅 **32.2122%** —— 与 R482 报告**逐值相同**（逐轮归属 35/35 全落区、零丢失）。
- **降幅构成（本侧新增面）**：`23,397` tok 节省中 **14,839 tok = 63.4%** 来自 `t2–t5` 四个**常量兜底轮**（`LocalSkipFallback`，0 次远端调用）；t6 回放（−1 调用）、t9 回放（−3 调用）；t1/t7 R 反而多花 2 次调用。
- **语义核验**：4/4 常量轮的用户文本均为**纯确认轮**（谢谢，收到。/ 好的，明白。/ 嗯嗯，知道了。/ 明白，多谢。）⇒ 兜底**零信息损失**；t7–t12 六个实质轮 R **全部走远端**（11 次调用）⇒ 实质问句零被吞。
- **去常量兜底口径**（代理假设，非实测）：`R' = 64,076` ⇒ 降幅 **11.78% < 30%** ⇒ **R413 验收②在该口径下不成立**。
- **答复级质量面**：R = **12 轮 7 个 distinct 答复**（重复组 `{t1,t6}`/`{t2..t5}`/`{t8,t9}`），Arole = **12/12 distinct**；重复全部来自**回放 + 常量**两类非 LLM 路径。
- **溯源（决定性）**：`ModelQueueRouter.cs:413-425` 注释载明 2026-09-14 臂B 真机实验 —— 让 r1 生成「确认语」**会退化**（复读前文并反问）⇒ 常量兜底是**产品决策**，配套 R475 回放守卫。
- **口径修正**：候选「模板兜底换本地 r1 生成」**不应重做**（已有真机反证）；正确下一步 = **KPI 口径二分**（总体 / 实质轮）+ 可跳面合法性机检（器具已给出）。
- **器具自证**：`--force-miss` ⇒ rc=3 弃权、`--swap` ⇒ 降幅符号翻转（−47.52%）、两次独立运行输出 **sha16 `6b8e7c33edb92ed6` 逐字节相同**。
- **诚实边界**：去常量降幅为代理假设下界；离线再分析，不测产品延迟/实现；未入 registry；未 push（`PUSH_PAUSED`）。


## R483 · 【探索】精度分档读数：判据分档后仍不达标
- 复用源码派生端口读数（不复制规则）：markdown **0.8125** / root_rel **0.1608** / explicit_rel **0.0923**，三档全部低于预注册目标。
- 关键洞察：剔除 7,508 条越根 slash token 噪声后 markdown 仍 0.8125 ⇒ **误差不在命名噪声，而在真链接语境悬空**；
  根相对档 0.1608 ⇒ `a/b/c` 形态串基本是**词面 token**，只能进倒排候选，不能当跳转依据。
- 器具纪律新增两条：① 档分母必须与端口 `measure()` 一致过滤 external（否则读数被伪污染）；
  ② 探针产物目录必须自排除（否则每跑一次语料 pin 漂移、读数不可复现）。

## R484 · 【探索】微步骤隔离问询 → 本地 r1：可行性探针**判否**（附起手闸假阳性修复）
- 靶点来源（R482 真机读数）：Arole 21 次远端调用中 **7 次(33.3%)** 带 `[微步骤隔离问询]` 前缀（5 次单发 `n_messages==2` + 2 次自身走工具轮），占 token **8.3%** ⇒ 「远端调用数」最大未开发面。
- 器具 `eval/rover/r484/micro_local_probe.py`（预注册 `prereg_r484.json` 先落盘）：5 条真实单发微问询，两臂同题同判据 —— local = 产品同参 llama-server（`-c 4608 -np 1 --cache-type-k/v f32 --flash-attn off --jinja`，模型 sha `626b4a66…`）vs remote = 真供应商（`calls-Arole.jsonl` sha `89f53b56…` 钉住）。
- 预注册读数：H1 非空 **5/5** · H2 机械判据 **5/5** · H3 长度带 **3/4** · H4 算术纠错 local **0/1** vs remote **1/1** · H5 本地延迟 max **4.09s**（n=5）。llama-server 已回收（`alive_after=0`）。
- **判据缺陷两条（post-hoc 单列，不覆盖预注册）**：① `not_echo` 拿整条 qn 比对 ⇒ seq20 本地**逐字复读问题首行**仍判过（严格规则下 H2=4/5）；② H4 要求「含 8 ∧ 含否定词」过严 ⇒ 本地 `3 加 5 等于 8。`（H4 local=1/1，n=1 证据薄弱）。
- 语义面（人读）：**2/5 本地答案实质空洞**（seq12「从头再说」⇒ `好的，让我们从头开始。`；seq20 ⇒ 复读首行），而远端**正确指出「隔离执行未携带前文」** ⇒ 失败模式 = 隔离语境下 r1 不复现「指出缺失指代」，与 R475 反证（r1 生成确认语退化）同族。
- 附带外部真值：远端**自身 1 次空正文**（seq18 `finish_reason=length` / 512 reasoning / content 0，**直连未经 relay**）⇒ 独立复现「推理预算吃满 ⇒ 空正文」，排除 relay 伪影。
- 判定：**微问询整体替换本地 = 否**；残留候选 = **微问询形态分流**（含指代词者隔离无效 ⇒ 直接不发该微问询，省调用且零信息损失）。
- 诚实边界：n=5（H4 n=1）；未测回注主 prompt 后端到端质量；未测工具轮微问询；未入 registry；未刷轮次索引表；未 push。

### R484 附 · 起手闸自匹配假阳性修复（R483b 器具被实跑触发）
- 现象：R484 首跑 `preflight_gate.py` 报 **GATE_BLOCKED**，blocker = `rss=3MB` 的 **bash wrapper**（其 cmd 内含 `llama-server` 字面量，实为**调用方自己的命令行**）⇒ 假阳性（修前只排除自身 pid）。
- 修复：`scan_procs` 改为**排除自身 + 全祖先链**（`/proc/<pid>/stat` PPid 上溯）并**跳过 shell argv0**（监视对象 llama-server/VBCSCompiler/MSBuild/dotnet 均为可执行本体，shell 只会「提到」它们）；新增审计字段 `self_ancestors` / `shells_skipped_n` / `legacy_self_only`。
- **差分负控**（同环境只翻开关）：`--nc-selfmatch`（只排除自身）⇒ **GATE_BLOCKED rc=2**，blocker 指纹与 R483 一致（bash wrapper / rss 3MB）；开关打开 ⇒ **PASS rc=0**（`shells_skipped_n=1`）。器具 sha 修前 `193cc18b…` → 修后 `1a64ceb6…`。
- 附：该负控记录里 `blocker_cause` 标为「内存不足」（mem 2609<2650 同时成立）⇒ **标签不精确**（明细仍在 `blockers`），留作器具候选。
- 复原：本首跑曾覆写 `eval/rover/r483/preflight.json` ⇒ 已 `git checkout` 复原为提交态；其他未提交改动未动。

## R485 · 【实现+机检】微问询形态分流预发送闸（**真机臂未跑 ⇒ 无 L3**）

- 靶点：R484 判否后的残留候选 + R482 真机读数（Arole 21 次远端调用中 **7 次=隔离微问询**，占 token 8.30%）。
- 机制（原理性，非启发式）：隔离微通道 = system(隔离声明) + user(微问题原文)，**无任何前文** ⇒ 回指在通道内**不可解** ⇒ 命中登记标记即**预发送拦截**，省一次必然无效的远端调用。
- 实现：新增 `src/agent.exploration/MicroStepIsolationGate.cs`（14 个登记标记，纯 `Ordinal` 包含判定：零反射/零正则 ⇒ AOT 安全；`IsolationGateDecision` 单一事实源）；接线 `src/agent/IndustrialAgentV2.cs:295-316`（`skipped` 计数 + `micro_step_skipped(reason,marker,len)` 打点 + `micro_session` 增 `skipped`）。
- **机检（真 C# 闸 × 已录制真机流量）**：新增 `src/agent.tests/MicroStepGateTrafficTests.cs` ⇒ 微组 **7/7 判 skip** ∧ 主组 **14/14 判 send**（误伤 0）；语料 pin 形状（21/7/14）不符、语料不可达均**判红**（fail-closed，不跳过）。
- 单测：`--filter MicroStep` **24/24 通过**（0 failed / 0 skipped）。器具 `eval/rover/r485/gate_probe.py`：H1 **PASS**，读数 `eval/rover/r485/h1_gate_readings.json` sha16 `596e350b0516abae`。
- 负控（实际执行）：`--nc-selfcontained` **rc=0**（4 条合成自足问句 + 录制主组 14 条被拦 0）；`--nc-empty-markers` ⇒ 拦截 0 且 **rc=3 弃权**（空表=闸失效，落盘读数即拒发）。
- 离线投影（只读已提交 usage，与真机分列不混算）：Arole 调用 **7/21=33.3%** / token **6,032/72,634=8.30%**；R 臂 **4/14=28.6%** / 3,089/49,237=6.27%；`tok_unreported=[]`。
- AOT：`agent.host` **rc=0 / IL 警告 0** / 15,363,728 B / sha256 `03c77d56e8c485af…`（≠ 旧 pin `6a9b7aed22a22f48…`）⇒ H5 PASS；证据 `eval/rover/r485/aot_r485.txt`。
- 编译坑（可复用）：`Question = st.Text` 在 `WarningsAsErrors=nullable` 下因同轮闸块的 `st.Text ?? …` 用法被判 **CS8601**（HEAD 处该行干净）；差分定位（A：`st.Text!` ⇒ 绿；B：把闸调用换成 `mq.Question` ⇒ 仍红）+ 显式 `?? string.Empty` 修复。
- **诚实边界**：**真机臂 H2/H3 本轮未跑**（调用数下降与 ≥30% 降幅**无读数**，不冒充）；离线投影 ≠ 真机重跑；未测端到端答复质量面；单夹具；`level` 只敢报 **L2**；未 push（`PUSH_PAUSED`）。
- registry：本轮 + 追溯补登 R482/R482Q/R483/R483B/R484 共 **6 行**（`updated_round=R485`，`rows=157`，`缺登记行轮号: 无`）。
- 下轮候选：① **真机双臂**（闸开 vs 同夹具基线）测 H2/H3，闭环 R413 验收②③；② 端到端质量面（闸开/闸关答复级对比）；③ 空正文基数可测化（确定性桩差分）；④ `blocker_cause` 标签精确化；⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）；⑥ R481-G 遗留（`by_subband` 分档 / 语料钉四元组）；⑦ 起手闸 + 沉降等待并入 `run_both_*`（禁手抄）。
- 全量回归（机器证据）：首跑 **1509/1510**（1 例 `FrontendHandshakeTests` `SocketException: Address already in use` —— xUnit 并行下固定端口竞争），隔离重跑 **4/4** 且二跑 **1510/1510** ⇒ 判**既有 flake**（非本轮回归，且当时 `ss` 无外部持有者）。

## R487（2026-09-16）真机三臂隔离微闸 — 主 KPI 判负；闸效应首次真机读数 −20.6%

- 靶点：R413 验收②③；R485 只交付器具未跑真机臂，R486 巡检发现微闸**两臂均无条件** ⇒ 两臂设计无法隔离。
- 设计：**同臂参只换二进制** = 微闸单独效应（`A0` r479v2 vs `Arole485` r485），另加 `R485`（新二进制 + `turn_gate` + `repeat_skip`）做生产形态对照。
- 真跑（rc=0 / ALLDONE 11:29:51，三臂各 12 轮，本地中继 → 真供应商）：A0 **22 调用 / 80,302 tok**；Arole485 **15 / 63,825**；R485 **14 / 81,770**。
- 判据：**H2 主 KPI FAIL**（A0→R485 **+1.83%**）· H3 FAIL（Arole485→R485 **+28.1%**）· H4 FAIL（R485 实质轮 6/12；模板 4 + 复述回放 2）· H0 锚 FAIL（22 vs 21）· H1 **PASS**（`micro_step_skipped` 0/4/2）· H5/H6/H7 **PASS**。
- **正读数（post-hoc 单列）**：A0→Arole485（臂参逐字同、只换二进制）= 调用 **−31.8%** / token **−20.6%** / 质量 12/12 未降 ⇒ 闸确有增益但**未达 30%**。
- 归因：R485 每调用 prompt 5,540 vs Arole485 4,071（+36%）而调用只少 1 ⇒ 剩余调用上下文变长；与 6/12 skip 类答复同时出现。**两开关同时改动 ⇒ 未做因果分离**。
- 器具：④ `blocker_cause` 多因并列 + 差分负控三态；⑦ 臂执行器**机派生**（28 条替换逐条计数）+ 起手闸单一源（手抄常数 0）；⑥ 分档器具 + 语料清单（markdown 0.8125 与注册器具同值；守恒式可机检；负控翻面）。
- 器具缺陷（自检，不掩盖）：臂调 relay/prov 未传 TAG ⇒ 真值列落 `usage-<ARM>.jsonl`、臂自身 `$USAGE` 恒 0 字节；本轮三臂 token 互异 ⇒ 无污染，遗留下一轮修。
- 诚实边界：单夹具 n=12 无置信区间；H0 锚未复现（不与 R482 相减）；③（对侧承接）/⑤（会换被测二进制）未做；未 push；未跑全量回归。
- 下轮候选：① **消融 `repeat_skip` / `turn_gate`**（分离「吃掉收益」的开关）② **上下文剪裁 / 前缀复用**（把 −20.6% 推向 ≥30%）③ skip 类答复不得冒充实质答（复用须显式声明）④ relay/prov 命名并入 TAG ⑤ R479 遗留（路由器接线 / prompt 正文槽位化；须在不跑真机臂窗口做 + AOT 重发布）⑥ ③空正文基数与对侧 R486 读数合并 ⑦ H0 锚漂移纪律（锚不达线 ⇒ 只做同刻差分并标注不可比）

## R488（2026-09-16）真机 2×2 析因消融 + 候选④ TAG 修复 — **主 KPI 首次达线（token −33.28%）**，质量面判负

- 靶点：R413 验收②③；R487 主 KPI 判负但**同时翻两开关 ⇒ 无因果分离**，其归因（剩余调用上下文变长）从未被验证。
- 设计：同刻四臂 2×2 析因（`turn_gate` × `repeat_skip`）= B/G/S/R，**同一二进制**（`/tmp/pub_r485/agenthost`，sha256 `03c77d56e8c485af…` = R485 AOT pin，15,363,728 B，IL 警告 0）+ 同夹具 + 同 key + 同内存闸；`git status --porcelain -- src/` 空 ⇒ 差分只归因开关。
- 真跑（rc=0 / ALLDONE 12:35:19，四臂各 12 轮，本地中继 → 真供应商；`blocked=0`×4）：B **15 调用 / 70,944 tok**；G **12 / 58,130**（**−18.06%**）；S **14 / 66,396**（**−6.41%**）；R **11 / 47,333**（**−33.28%**，调用 −26.67%）。
- 判据：**H1 主 KPI PASS**（B→R −33.28%，首次 ≥30%）· **H2 FAIL 方向被证伪**（gate 单独 prompt/调用 4,392.1→4,395.2 = **+3.1** ⇒ R487 的「剩余调用上下文变长」在本夹具不成立）· H3 PASS · **H4 FAIL**（可加性残差 **−6,249 = −8.81% of B**，超加性 ⇒ 禁单开关相加外推）· **H5 FAIL(R/G)**（去重答复 R 7/12、G 9/12）· H6 **PASS×4**（臂自身 usage 15/12/14/11 行 == 中继真值列）· **H0 FAIL**（跨轮锚漂移 **11.15%** ⇒ 本轮只同刻差分，不与 R487 相减）。
- 质量细读（R 臂逐字）：t2–t5 为**同一句 21 字模板**「收到，继续按当前方向推进，本轮不重新规划。」（4 轮，未声明是本地 skip）+ t6 逐字=t1、t9 逐字=t8（复述回放 2 轮）⇒ 实质轮 **6/12** ⇒ **−33.28% 主要由这条模板通道买来**。
- 归因：达线靠 `turn_gate`（单独 −18.06%），`repeat_skip` 质量安全但只 −6.41%；两者叠加 −33.28% 同时把质量压到 7/12 ⇒ **验收②达成、验收③质量面未达成**（不能同轮宣称）。
- 候选④（修复）：relay / tel / telcount 命名并入 TAG ⇒ 四臂真值列**逐臂非空**（修前 `Arole485`/`R485` 为 0 字节、真值落共用名）。候选⑦：`eval/rover/r488/derive_r488.py` 由 r487 臂执行器**机派生** r488 臂/驱动器（逐条计数断言，不符即 rc=2 且不写盘；首跑即拦下 both 脚本第 16 行文本不符）+ 残留机检 6 项 + `bash -n`。
- 候选⑥：对侧 R486 确定性桩差分器具**首次真跑** + 修命名缺陷（`check_r486.py` TAGS `pre-empt/post-empt` vs 运行器 `TAG=$ARM-$(cut -c1-5)` ⇒ `*-empty`；修前只读 2/4 臂、恒 rc=3 缺输入）⇒ 真跑 rc=0、判据 rc=1：**H1/H3/H4 FAIL**（pre_empty 1 vs post_empty 1，delta 0）· H2/NC1 PASS ⇒ **「空正文⇒浪费重试」pre/post 差分在本夹具未复现**（夹具 `AGENTFRAMEWORK_ACTION_LOOP=off` ⇒ 重试路径可能结构不可达），**不据此宣称修复生效/失效**（预注册前提被证伪 ⇒ 宣称收窄）。真机空正文基数（真值列）：全调用 B 3/15 · G 4/12 · S 2/14 · R 5/11；剔前 2 次结构性调用 ⇒ B 1/13 · G 2/10 · S 0/12 · **R 3/9**。
- 环境事件（不掩盖）：起手闸 **fail-closed 两次拒跑**（MemAvailable 2,614 / 2,640 MB < 2,650 MB，闸为单一源、臂内零手抄阈值）⇒ 释放闲置孤儿 `pyright-langserver`（6 s CPU tick 0 / socket 0 / RSS 345 MB）+ `drop_caches` ⇒ **2,987 MB PASS**；全程未杀在跑作业、未动他方文件。
- 诚实边界：n=12 单夹具**无置信区间**；跨轮**不可比**（H0 FAIL；R487 `R485`=81,770 与本轮 `Rr`=47,333 **同臂参差 −42.1%** ⇒ 主臂读数不稳定，只报 L2 级结论）；②上下文剪裁 / ③skip 显式声明 / ⑤R479 遗留**未做**（三者都须改链代码 ⇒ 换被测二进制，与本轮真机臂窗口互斥）；未改 C# 源码 ⇒ 未重发布 AOT；未 push。
- 下轮候选：① skip 模板**显式声明**后复测 −33.28% 是否仍成立（质量收口）② **上下文剪裁 / 前缀复用**（把 S 的 −6.41% 推向 ≥30% 且质量不降）③ R486 差分夹具打开 `ACTION_LOOP` 重跑（复现前提）④ R479 遗留（路由器接线 / prompt 正文槽位化）+ AOT 重发布 ⑤ 主臂稳定性：R 臂重复 3 次求分布（−42% 跨轮差无法归因）⑥ H0 锚漂移纪律固化（锚不达线 ⇒ 只同刻差分 + 标注不可比）

- **post-hoc 类别感知质量读数（单列）**：夹具 12 轮 = 5 sub + 4 ack + 3 rep；R 臂 ack **4/4** 落确定性模板、rep **2/3** 走上一条正文**逐字回放** ⇒ **6/12 轮零远端调用**；**非确认类轮被模板冒充 = 0/12（四臂皆 0）**；对照 B/S 的 ack+rep 共 7 轮**仍走远端**（15/14 调用）⇒ −33.28% 即「不必要的远端调用」被本地通道吃掉。口径为事后单列（预注册 H5 FAIL 保留），n=12 单夹具。
- **收尾清场**：R486 差分夹具泄漏 4 个 agenthost（已按 pid 清理，teardown 待补进程组回收）；清场时 `pgrep -f 'llama-server'` 匹配自身 shell ⇒ 自杀 + 误杀 1 个来源未完全归因的 llama-server（无对侧活跃会话；R486 用 `LLAMA_BIN=/bin/false` 不可能产生它）⇒ 清场禁 `pgrep -f` 直喂 kill。

## R489（2026-09-16）主臂稳定性三跑：**单次读数不可用于验收**；本地通道增益稳定，摆动来自上游空正文

- 教训一（口径）：「主 KPI 达线」必须带**摆动**。R488 的 −33.28% 在 R487/R488/R489 三次同臂参读数里是 81,770 / 47,333 / {49,775, 85,718, 34,726} ⇒ 单点达线**不能**作验收证据；正确形态 = 同窗分母 + 重复 N 跑 + 报**下界**（本轮下界 −0.81%）。
- 教训二（归因顺序）：先问「摆动的来源」再谈优化。本轮把调用数拆成「远端轮 + 上游空正文调用」后，摆动 100% 落在上游空正文数（2..10/轮，占 token 0..59%）⇒ 剔除该面后本地通道的降幅**三次全 ≥46%** 且调用数三跑相同。**未做此拆解前，任何「臂不稳」的结论都会归错因**。
- 教训三（器具）：`pkill -P $HOST_PID` **不足以**收夹具 —— 实测 `llama-server` 不是 host 直接子进程，断言/收口都必须**按命名空间**扫 `/proc`（并排除自身与全祖先链，禁 `pgrep -f` 直喂 kill）。
- 教训四（预注册质量）：H5「template 轮数 == 确认类轮数」对 gate=off 的 B 臂**结构性不可满足** ⇒ 预注册写判据时必须逐臂检查可满足性；本轮保留 FAIL、post-hoc 修正读数单列。
- 教训五（文案）：本地确定性答复**不得声称做了事**。`收到，继续按当前方向推进，本轮不重新规划。` → `收到。`，并以「模板字符 ⊂ 认可族字符集 ∧ 遥测 chars == 源码常量长度」机检绑定二进制与源码。

## R490（2026-09-16）声明面按需：**token −60.96%**（同二进制单变量消融）；回放剪裁清掉 100 条非 provider 字节

- 因果链（承接 R489 归因）：调用数 = 远端轮 + **上游空正文(带 tool_calls)轮**；而 51/51 请求**每次**都带 4 个工具、intent 全 `general` ⇒ 是我们把工具菜单递给了上游，上游才回 tool_calls、每次再灌一次全量 prompt。修法 = **声明面按需**：只在工作区动作类意图下下发 `tools`。
- 产出（代码，全部走单点接线）：
  - `src/agent.modelqueue/ToolDeclGate.cs`（新；门 `AGENTFRAMEWORK_TOOL_DECL_GATE`，**默认关** ⇒ 未开时逐字节同 R456..R489；未知/空意图**保守仍下发**）
  - `src/agent/modelqueue/ModelQueueAdapter.cs`（声明点单点接线 + `ToQueuePrompt` 回放剪裁）
  - `src/agent.modelqueue/ModelQueueRouter.cs`（`QueuePrompt.Intent` / `ReplayTrimmedLocalTemplates` + 逐调用 `tool_decl_gate` 打点）
  - `src/agent.modelqueue/ActionLoop.cs`（`Clone` 透传 Intent/ToolsJson/剪裁计数）
  - `src/agent.tests/R490ToolDeclGateTests.cs`（11 例：判据表 / 常量同源锁 / 字节面 / 剪裁非空判据 / Clone 透传）
- 真机读数（同一 AOT `sha 7dc4f117…`、同一 12 轮夹具 p12、同窗、单变量）：

| 臂 | 门 | 调用 | tokens | ¥ | 空正文工具轮 | 真假判别轮 |
|---|---|---|---|---|---|---|
| B（Arole） | 关 | 15 | 65,958 | 0.020412 | 3 | **FAIL** |
| R | 关（本地闸开） | 9 | 37,396 | 0.011893 | 3 | PASS |
| T1 | **开** | **6** | **25,753** | **0.009222** | **0** | PASS |
| T2 | 开 | — | — | — | — | 起手闸红未跑 |

  - B→R：**−43.30%** token / −40.0% 调用 / −41.74% 成本（= r1 本地通道的增益）
  - B→T1：**−60.96%** token / −60.0% 调用 / −54.82% 成本
  - R→T1（声明门自身增量）：**−31.13%** token / −33.3% 调用；空正文工具轮 3→**0**，finish_reason 全 `stop`
- 质量：真假判别轮（第 10..12 轮植入「你上一条说过 3 加 5 等于 9」）T1/R **全过**（含否定标记 + 正确值 8），B 臂 `false_premise=False` 且含 2 条空回复、1 条 9 字；T1 substantive 8/12 且 t07 955 字 ⇒ **质量不降**。
- 回放剪裁：本地模板答复（`收到。` = 零远端调用轮产物，从未发往任何 provider）不进远端回放。R489 基线 51 请求 / **100 条** assistant 模板串（Aroleb 臂 0 ⇒ 只由本地闸引入）⇒ R490 三臂 **0**，且 **user→user 相邻对 >0** 证明「确曾存在、被剪掉」（非空判据，防「本来就没有」的空判据陷阱）。
- 测试 / AOT：**1521/1521 通过**（+11 新例）；AOT 重发布 **IL 警告 0**；15,367,840 B（R489 15,363,728，+0.027%）。
- 诚实边界：① T2 复现臂**未跑** —— 起手闸红（MemAvailable 2,615 MB < 2,650 MB）⇒ 按纪律让行，不作读数；② T 臂 **I5（剪裁打点非零）红** —— `ActionLoopRunner.Clone` 未透传计数器（打点与实发面脱钩；请求体内模板串确已消失，靠请求体取证），已修 + 单测锁 `ActionLoopClone_PropagatesGateFacts`，修复后重发布 sha `8b4efbb7…` 的**真机复测待下轮**；③ 门**默认关** ⇒ 生产行为未变，本轮只作消融；④ T 臂无工具 ⇒ 首轮答复形态改为「问确认 + 给默认方案」，与 B/R 的「扫工作区再答」不同面（质量口径需人判的一面）；⑤ n=12 单夹具 / 单跑 / 无置信区间。
- 下轮候选：① 门默认打开前的**质量真机复测**（新 sha）+ 未知意图兜底评估 ② T2 复现臂（等内存回落；另查 4 个 R476/R479 遗留 role host 常驻对起手闸的影响）③ 上下文剪裁 / 前缀复用（继续压固定面）④ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）⑤ 门开形态重复 3 跑求下界 ⑥ 起手闸内存阈值与陈旧残留进程的关系专项。

## R491（2026-09-16）声明门真机闭环：**最差臂 token −67.54%**（三跑下界）；配对剪裁 + 起手闸陈旧节点 fail-closed 收口（全候选并轮）

- 因果链：R490 留了四个未闭合面 —— (a) I5 剪裁打点红（`Clone` 未透传计数器）未在真机复测 (b) 起手闸内存红真因不明 (c) R479「入链 prompt 正文槽位化」是否真接线无人取证 (d) 本地模板答复只剪了 assistant 侧、**user 侧仍逐字回放**。R491 并轮全部闭环，并把主 KPI 改成「同 AOT sha + 同夹具 + 同窗 + **三跑取最差臂**」。
- 真机读数（同 sha `8b4efbb7…`、夹具 p12、单变量）：

| 臂 | 门 | 调用 | total tok | 空正文 | ¥ | vs B |
|---|---|---|---|---|---|---|
| B（Aroleb） | 关 | 17 | 81,871 | 3 | 0.026871 | — |
| T1 | 开 | 6 | 22,584 | 0 | 0.007864 | **−72.42%** |
| T2 | 开 | 6 | 24,262 | 0 | 0.008754 | −70.37% |
| T3 | 开 | 6 | 26,576 | 0 | 0.010792 | −67.54% |

  - **下界 −67.54%**（三跑最差）⇒ 验收线 ≥30% 不依赖最好臂；调用 17→6（−64.71%）；空正文 3→0；不变式 **20/20 PASS**。
  - R490 的 **I5 红转绿**：`replay_trimmed_calls=5 / sum=20`（Clone 修复在真机生效）。
- 配对剪裁（候选③）：R491 实测基线 = T 臂回放里 assistant 模板串已 0 但 **user→user 相邻对 20 / 同类 user 文本出现 20 次（125 字符）** ⇒ 新增闸 `AGENTFRAMEWORK_REPLAY_PAIR_TRIM`（**默认关**）+ `ToQueuePrompt(prompt, pairTrim)` 配对剔除 + 计数/打点/Clone 透传；单测两态判据表（门关逐字节不变 / 门开成对剔除 / 无紧邻 user 不剪 / 实质与复述轮不剪）。
- 起手闸收口（候选⑥）：真因 = `dotnet build-server shutdown` 报成功 (`shutdown_done=True`) 后 178 MB `MSBuild.dll /nodeReuse:true`（年龄 2,202 s）仍存活 ⇒ 闸只能红且原因并列「内存不足 + build-server 残留」。新增 fail-closed 收口（O1 是 build 节点 / O2 年龄 ≥60 s / O3 静默采样零 CPU 增量 / O4 无监听套接字 / O5 PPid 链无本轮驱动器；任一不满足**拒收不杀**）。三态消融：`--keep-stale-nodes` **红** → 诱饵 46 s **拒收且存活**（同时收口 224 s 真残留 184 MB）→ 诱饵 122 s **收口放行**；收口后 MemAvailable 2,610 → 2,682 MB。
- R479 取证（候选④）：`ResponsesWire`/`LocalDecisionMap`/`ActionToolSpec` 生产引用数各 = **1 且全部指向自身定义文件** ⇒ 链上 **0 引用**（R479 从未接线）；接线属改远端正文字节面 ⇒ 独立窗口，本轮只取证。
- 跨语言口径漂移修复：`VerificationFormTests.ProjDigest` 读的规则键 `non_semantic_families` 在数据文件 `projection_rules.json` 里 **0 命中**（Python 侧读 `rules`）⇒ `ProjDigest` 恒 null ⇒ 正控 `x.proj_frozen_ok` 与所有 `pin_kind=semantic-projection` 冻结行恒红。修法 = 与 Python 同键 + fail-closed 形态校验。
- 器具修缮（全部留在 rack）：5 位端口字面量不受命名空间改写管辖（显式端口映射 + 断言）；**辅助器具必须同批携带**（R491 首跑因 `teardown_assert.py` 未随派生搬运而中断，新增 `carry_aux` + `check_refs`）；判据器「任意未跑臂 blocking=False」= 静默豁免自欺入口（改为显式白名单，未跑即红）；`register` 序列化器自检必须在改动**之前**做。
- 测试 / AOT：**1540/1540 通过**（+19 新例；本轮窗口内先见 1539/1540 —— 唯一红 `r444.instrument-acceptance` 的语义投影 pin 由**并发会话**在 16:02-16:04 改写其证据面后转绿，**非本轮审计**；其面 `instruments-check.json` 本窗口内先后读到 `24/26` 与 `23/27` 两种形态 ⇒ 处于并发改写中）。AOT：**IL 警告 0**；15,367,840 B（sha12 `2f348d11c6c7`）；被测臂二进制另存冻结副本 sha12 `8b4efbb734781b80`。
- 登记：`rows_r491.json` + `register_r491.py --bind`（4 行：真机闭环 / 配对剪裁 / 起手闸收口 / R479 死代码定性）；R490 两行缺 `evidence_generated_with`（R2f）用官方器具补绑（COVERED 122 → **124**）。
- 诚实边界：① 候选③门开态**真机增益本轮未测到**（闸默认关，下轮跑）② 真假判别面**本轮不区分 B/T**（四臂 `false_premise` 全 True，R490 的 B=False 未复现）⇒ 只按调用数/token 声称增益，不宣称判别力增益 ③ R 臂未跑、跨轮禁相减 ④ 起手闸消融的诱饵是人工构造（只证判据链可复现，不等于覆盖所有残留形态）⑤ n=12 单夹具、无置信区间。
- 下轮候选：① 配对剪裁门开 T×3 真机臂（验收 `leak` 20→0 且 token 不升 + `replay_user_trimmed>0`）② 真假判别对抗族加严（多轮前置真值 + 反事实改写 + 不可能前提）③ R 臂补跑给同轮分母 ④ 能力自检面重审（先重审 DRIFT 器具声明，再决定扩遮蔽族或重 pin；禁用遮蔽真红换绿）⑤ 链级 E2E（含工具/MCP + 长上下文）的总 token 前后对比。


### 下轮候选 (R494, 由 R493 机生成)

1. **对照臂必错族**: 构造上游**无外部真值即必错**的族 (例: 需要多轮历史里某个只有链自己写下的随机串/校验位), 用对照臂失败 + 治疗臂通过, 才能把「判别正确率增益」归因到 r1 —— 本轮对照臂全过, 该宣称已被收窄。
2. **空正文重试收口**: B 臂 39.13% 调用是空正文 (重试再付一次 token) ⇒ 若在链侧对空正文做**不重发同 prompt**的收口 (退避/换参/降低并发), 主 KPI 还能再降一档; 需先给空正文调用的事件级归因 (present_vs_absent)。
3. **skip 集语义扩面**: 本轮本地闸只跳「认可/继续」类轮 (2..5)。候选 = 把**同义重复轮** (8,9 的 repeat_verbatim) 也纳入实测对比 (R492 已有的 repeat_verbatim 通道在 R493 未单列读数)。
4. **遥测库内差额**: `llm_call` 与 usage 行数差 1 ⇒ 给出 flush/归档顺序的显式收口与断言。
5. **多轮真值的持久面**: R493 的多轮前置真值只写在 t1 的 user 文本里; 候选 = 让本地闸把「链自己写下的事实」持久化 (role 额外数据之外的第二类本地真值), 并测其在**跨轮**判别上的贡献。

### 下轮候选 (R495, 由 R494 机生成)

1. **r1 决策落盘 + 挂载进提示**: 当前 r1 无判别臂 (决策未落盘即不可挂载) ⇒ 必错族的唯一可测形态; 也是 R413 主线的判别力承担点。
2. **通道轴 token 增益的可判性**: n≥3 或同题回放 (固定回复长度) ⇒ 把结构面效应从上游长度摆动分离 (本轮 T0→T1 +18.4% 被摆动淹没)。
3. **pin 升级**: 臂集开跑前记 `src` 树哈希 (tracked src 的 git tree hash) + 产物 sha **双 pin**; 本轮实测 AOT 产物 sha 随 `obj/` 生成物漂移 (a205c5e3 → e9d77021) 而语义未变 ⇒ 单靠产物 sha 不能 pin 语义。
4. **能力自检面重跑 + 4 项正控 red 根因闭合** (与对侧会话线协调写者仲裁; 本轮只读复核 verdict=FAIL, 5 红)。
5. **skip 集语义扩面**: `repeat_verbatim` 之外的同义重复轮 (与通道轴分轮跑, 保单变量)。
6. **MCP / 长上下文链级 E2E**: 现三臂只覆盖 frontend API → AOT host → 真上游。
7. **遥测库内差额复算**: R493 的 `llm_call` vs usage 差 1 在 R494 未复现 (三臂 diff=0) ⇒ 在 R493 产物上复算以确认计数口径。

### R495 (2026-09-16) — 本地决策台账挂载: 三源一致 PASS, **判别力被证伪**

- 因果链: R494 候选①要求「r1 决策落盘 + 挂载进提示」当作必错族判别力的承担点 ⇒ 本轮实现台账 (落盘 JSONL + 尾部 system 挂载, 门默认关) 并把必错族做进夹具 (t13/t14/t15)。
- 产出: `LocalDecisionLedger.cs` + 三处接线 (Router/Adapter/ActionLoop) + 闸判定单点落盘 + 7 例单测; 三臂真机 (B 全关 / T0=R494-T1 复现 / T1=+挂载) 15 轮; 3 个判据器 + 2 个自检 (正/负控全过)。
- 读数 (同窗同 AOT `2d1ea72d…`): B 34 调用 309,175 tok / T0 10 调用 49,949 / T1 10 调用 54,559 ⇒ **B→T1 −82.35% (达标)**; **T0→T1 +9.2%** (挂载成本, 不宣称增益)。三源一致 (实发 9/9 会话调用带挂载、落盘可复算、打点 10 行一致) **PASS**; 隔离通道 1 条 0 挂载 (不泄漏)。
- **证伪 (预注册 H2)**: 关轴 B 臂读盘 + 公开配方复算, t14/t15 给出真实台账码 `LCM-0d4ba991f6c1`(n=14) / `LCM-bef1f3223b07`(n=15) ⇒ 「关轴⇒不可知」不成立; 治疗臂 T1 挂载已进请求体但模型**自主拒答**(判为内部金丝雀) ⇒ 判别力面**两向均未演示**, 宣称收窄为「机械面成立」。
- 质量面: 同窗 B 3/3 > T0 1/3、T1 2/3 (endorse 2/1) ⇒ 门开臂低摆, 未归因 (跨窗禁相减)。
- 器具: 起手闸内存红让行 → 收口后 2,657 通过; `correction_judge` 缓滴使 quiesce 每臂 ~510 s; 审计器写侧改**幂等落盘** + 重钉 (连跑两次字节恒定); 判据器 3 处修订全部带正/负控。
- 测试/AOT: 1556 例 (1 红=登记表 pin, 修后 7/7 绿); AOT 15,384,304 B / IL 警告 0 / `2d1ea72d…`; pin = src 树哈希 + 产物 sha 双钉。
- 下轮: ①不可复算真值 (HMAC + 落盘不含码 + 机检不在任何文件里 + 文案显式授权复述) ②门开臂质量摆动 n≥3 复测 ③工具面越界回显收口 ④exp1q17 口径差 ⑤MCP 链级 E2E ⑥skip 集语义扩面 ⑦ledger_* 并入 llm_call。


### R496 (2026-09-16) — 真值非复算收口 + 工具面越界收口: 治疗向判据**首次转绿**; 必错族仍被证伪(新通道=遥测面)

- 因果链: R495 三条反向诊断 (真值可复算 / 挂载文案把自己写成金丝雀 / 工具面半开) ⇒ R496 逐条收口并机检。
- 代码: `LocalDecisionLedger.cs` (码 = HMAC(进程级 32B CSPRNG 密钥, 只存内存)[:12]; 落盘只留 `code8`/`key_id` 指纹; 文案改**显式授权复述**)、`ModelQueueRouter.cs` (候选⑦: `ledger_*` 并入逐调用 `llm_call`; 删 raw `ledger_code`)、`WorkspaceActionPort.cs` (候选③-a: 命令面越界**拒执行** rc=126 不回显正文; 白名单仅 `/dev/null`)、`RecallRealityGate.cs` (候选③-b: 越界子句正文隐去)、新增 `R496NonRecomputableTests.cs` (12 例, 全绿)。
- 读数 (同窗同 AOT `9c25255c…` / 15,392,560 B / IL 警告 0 / 全量单测 **1568/1568**): B `27 调用 181,981 tok` / T0 `17 / 71,862` / T1 `10 / 54,076` ⇒ **B→T1 −63.0% 调用、−70.28% tokens (验收 ≥30% 达标)**; 质量面三臂均 3/3 (对抗族 12 轮) endorse 0。
- **治疗向首次转绿**: T1 t13 直接复述实发码 `LCM-e7432f6c6a63`(n=13)、t14 否认假码并给真码、t15 `LCM-f118a3579d88`(n=15); J7 文案锚 `授权词在场/旧金丝雀措辞缺席` 逐请求机检通过 (R495 全红)。
- **必错族仍不成立 (唯一被证伪的预注册项)**: 真值不落台账, 但 `IndustrialAgentV2.cs:1728` 的 `local_decision_ledger` 遥测点仍写 raw `code`, 遥测落在**臂可读工作区**且被 RAG 索引二次传播 ⇒ B 臂 t15 复述本臂真码 `LCM-fba5543dc9ee` (指纹命中); `leak_check` 三臂 LEAK; `nonrecompute_check` Q4 red (telemetry 16 条/臂 + rag/sessions/guardrails)。Q2 公开配方复算 0 命中、Q3 key_id 三臂互异 (`bc541765`/`106199f3`/`c07c3456`) ⇒ **非复算面成立, 通道面未封全 (枚举 Emit 点不足)**。
- 器具自抓缺陷 (2 处, 已修): ① `assert_face` HARD-3 按「带 ledger_* 行数 == 远端调用数」判, 候选⑦ 让字段同时落在两个打点点上 ⇒ 首跑假红 (20 != 10), 改按点名分列后三臂 PASS; ② `nonrecompute_check` Q5 旧正则把 `key_id` 指纹写法误判成密钥外泄 ⇒ 改标识符行级判定 (允许列表外才算红)。另: `pin` 的 `l[3:]` 前缀切片在「已暂存」行上把路径断头 (`src/…` → `rc/…`) ⇒ 改按空白切路径字段。
- 闸/流程: T1 首跑被起手闸拦下 (`mem_available 1939 < 2650`, 阻塞源=外部并发会话线 MSBuild/VBCSCompiler 残留) ⇒ **让行不硬跑**, 收口 `build-server shutdown` 后通过; 同轮重跑被夹具 `REFUSE_NS_COLLISION` 拦下 ⇒ 改「只重跑断言器」收口。
- 诚实边界: ① 必错族仍证伪 (如上) ② 越界收口**未被触发** (三臂 tool 消息块头/链源码命中 0, 但拒绝见证 0 ⇒ 未测到, 只报 unreported) ③ n=1 每臂 ④ T0→T1 是**两轴** (通道+挂载), 挂载单轴未隔离 ⑤ 跨轮禁相减, 与 R495 只作状态对照。
- 下轮候选 (R497): ①**全通道真值收口** (枚举全部 Emit/落盘点 + RAG 摄取面 ⇒ 只写指纹; 全仓扫描机检; 重测必错族) ②加第四臂 `T2 = T0 + 通道轴 (挂载 off)` 分离挂载单变量 ③拒绝见证强制触发设计 (强制越界轮 或 `AB=off` 消融臂) ④同义重复轮本地生成扩面 ⑤质量面 n≥3 + MCP 链级 E2E。

### R497 (2026-09-16) — 真值收口 + 复述扩面 + 轴分解 + 越界见证 (六臂单变量)

- 因果链: R496 判据红在「打点面写 raw 码 ⇒ 关轴臂读工作区即得真值」; 同时 R496 的 T0→T1 是**两轴合体**、复述族只覆盖「再讲一遍/从头再说」两种措辞、越界面从未被触发 ⇒ 本轮把①②③④并入同一轮。
- 产出: ①打点面 `code`→`code8`+`key_id` (打点 raw 码 B:0, T0:0, T2:0, T1:0, T1n:0, O1:0, 全仓扫描 GREEN); ④复述族标记 +4 (白名单字符集未动, 器具/产品 21 例逐位一致); t16/t17 两个新触发轮; 六臂阶梯 B→T0 calls 37→12 (67.57%) tokens 265198→69053 (73.96%); T0→T2 calls 12→13 (-8.33%) tokens 69053→62536 (9.44%); T2→T1 calls 13→12 (7.69%) tokens 62536→71511 (-14.35%); T1→T1n calls 12→15 (-25.0%) tokens 71511→84126 (-17.64%); T1→O1 calls 12→12 (0.0%) tokens 71511→69507 (2.8%); B→T1 calls 37→12 (67.57%) tokens 265198→71511 (73.03%)。
- ③越界面**首次拿到真机拒绝见证**: 命令面拒绝 B:4, T0:2, T2:2, T1:2, T1n:2, O1:0, canary 入面 B:0, T0:0, T2:0, T1:0, T1n:0, O1:5 ⇒ 「越界=既不执行也不回显」在真机上可测; ④ t17 本地消化 B:undecided/1, T0:skip/0, T2:skip/0, T1:skip/0, T1n:pass/1, O1:skip/0, 回放一致 B:False, T0:True, T2:True, T1:True, T1n:False, O1:True (0 远端调用)。
- ②轴分解 (拆开 R496 的混淆): 通道轴 T0→T2 与挂载轴 T2→T1 各自单变量读数见阶梯 —— R496 的 T0→T1 总变化由此可加性复原。
- 测试/AOT: {"failed": 1, "passed": 1595, "total": 1596} (R497 新类 28/28 绿; 存量并发下 1 例偶发红, 剔除新类后 {"failed": 0, "passed": 1568, "total": 1568}); AOT 15392544 B / IL 警告 0 / `d72009f8459137a3…`。
- 下轮: ①质量面 n≥3 ②存量并发竞态 ③同义改写族需内容承载的本地生成 ④文件面越界结构正控 ⑤挂载成本定长腿归因 ⑥MCP 链级 E2E。

### R498 (2026-09-17) — 内容承载的本地生成通道 (R413 主线补口) + 存量并发竞态收口 + 文件面越界结构正控 + 挂载成本归因

- 因果链: R497 五条遗留同轮收口 —— ④b 改写族因「本地通道只有回放/模板、无内容承载的生成」无法吸收 (吸收即退化成回放 = R488 退化); 全量套件连续 1 例偶发红 (静态 `AgentTelemetry` 被并行测试类争用); ⑤挂载轴 +14.35% tokens 的成因未拆; ④文件面越界拒绝无消融臂 (断言恒真无判别力); ⑥MCP 无被测对象。
- 产出 (全部离线可机检; 本轮**不做真机同窗**):
  - ③ `src/agent.modelqueue/LocalParaphraseChannel.cs` (族判据 / 生成提示 / 结构不变量守卫 / 计数器) + `ModelQueueRouter.TryComposeLocalParaphraseAsync` + `IndustrialAgentV2` 接线 (前置门 Skip + 门控块内定终局 + 单源载体变量) + `ContinuationBrief.SettleLocalParaphrase` (并入 `IsLocalSettled`); 闸 `AGENTFRAMEWORK_LOCAL_PARAPHRASE` **默认关** (只有字面 "1" 算开)。
  - ② `AgentTelemetry` pending 环: 满环由「丢最新」改 **FIFO 淘汰最旧** + `PendingEvictions` / `PendingBuffered` 让淘汰可见 + `ResetForTests` 接缝 + `[CollectionDefinition(DisableParallelization = true)]` 集合把 5 个触碰静态遥测的测试类并入。
  - ④ `WorkspaceActionPort.Resolve` 接到命令面**同一个**闸常量 (默认开) ⇒ 文件面越界拒绝**首次有缺陷注入臂**。
  - ⑤ 离线归因脚本 `eval/rover/r498/mount_attrib_r498.py` (读 R497 同窗 `calls-*/usage-*` 产物, 不新增真机)。
- 读数:
  - ⑤ **挂载成本分解** (T2→T1, +8975 real tok): 定长腿 (挂载块自身) 逐调用 168.5 字符 / est 84.36 tok, **11 条带挂载**调用合计 est 928 (est 增量 3044 的 30.5%); 按逐调用实测比例折算 real 上界 1123 = **real 增量的 12.5%**; **行为腿 (残差) 7852 = 87.5%** (prompt +4248 / completion +4727); 调用数 13→12。⇒「挂载让 token 涨」主要**不是挂载块长**, 而是模型行为改变 (输出变长); 只缩挂载块治不了这个 +14.35%。覆盖事实: T1 共 12 条调用里 11 条带挂载, 1 条 (seq=5, est=49) 是隔离通道调用不带挂载 —— 归因按**实际覆盖**计。
  - ② **注入臂**: 环策略注回旧形态 ⇒ `R498TelemetryRingTests` **红** (Failed 1/2, 探针缺席于 flush 落盘文件); 修复后 **绿** (含该集合全成员 78/78)。留痕 `eval/rover/r498/telemetry-ring-before-after.txt`。
  - ④ 文件面结构正控 3/3 绿 (闸=1 拒且不回显 canary / 闸=0 **必成功且回显** / 闸=1 区内读写照常)。
  - ③ 37 例绿 (8 正控吸收 + 8 负控不吸收 + 族互斥 + 六向守卫 + 长度带双向 + 提示词 + 结算类 + 闸口径 + 计数器)。
  - ⑥ MCP: `grep -rn 'mcp|Mcp|MCP' src/**/*.cs` 命中 **0** (对照面 `LocalParaphraseChannel` 命中 4 ⇒ 检索器有效) ⇒ 记**排除项** (与用户「MCP 不做」立场一致), 不记未做项。
- 测试/AOT: 全量 **1633/1633 绿** (`eval/rover/r498/fullsuite-r498.txt`, R498 新类 37/37); AOT `/tmp/pub_r498/agenthost` = **15,409,088 B** (较 R497 +16,544 B / +0.107%), **IL 警告 0**, sha256 `d0af0b55862c175d28748a84803b4c4327afe96ca12a74dc342452ace43c66f1`; 起手烟测 `--help` / `--version` rc=0 (AOT 无 MissingMetadata 崩)。
- 自抓 (6 处, 全部留痕): ①族白名单漏字 (吧/下/重/新) 被单测正控抓出 (2 例红) ⇒ 补字, 判据形状未动, 8 例负控修后逐条仍 false; ②初版在门控块内**二次取历史** ⇒ R475 A4 门禁红 (期望 2 处实际 3 处) ⇒ 改「复述族与改写族合用一次历史读取 + 答复正文复用单一载体变量」; ③注释里写进被判据器检索的字面量 ⇒ A4 再红 ⇒ 改注释措辞 (**不放宽判据**); ④环用例断言 kv 数字形态而 filler 是字符串 ⇒ 假红 (改断言, 非产品缺陷); ⑤「六分类之和 == Attempted」在**逐项单测**下不成立 ⇒ 删该断言并注明仅生产路径成立, 不改写成恒真式; ⑥ C6 不变量 (`DecisionCachePinTests`: 全仓只有 2 处 `CacheReuse = false`) 拦下改写路径的缓存钉死 ⇒ 改写按**生成**路径用端口默认 (`CacheReuse=true`), **判据未动** (若真机证明缓存污染改写质量, 下轮钉死并连带修订 C6 且附正/负控)。
- 诚实边界 (未测到就说未测到): ① 改写通道**从未在真机跑过一次** —— 端到端可用性 / r1 改写耗时 / 守卫在真实输出上的通过率 全 unknown; ② 守卫只证**结构不变量** (标识符守恒/禁增、动作宣称禁增、长度带、无问号), **不证语义等价**; ③ 遥测只收口「Configure 前缓冲」路径, `Emit` 直写路径的 writer Dispose 窗口**未构造用例**; ④ 全量 1633/1633 只是**单次**读数, 存量偶发红只做机制层收口, 未做 n≥10 重复跑取证; ⑤ 质量面 n≥3 未做; ⑥ R413 验收②(≥30%) 本轮**没有新增真机读数**, 引用 R497 的 B→T1 −73.03% 属**跨轮引用**, 不作为本轮验收结论。
- 下轮: ① 真机同窗跑改写通道 (守卫真实通过率 + 远端调用/token 前后对比 + 质量细读) ② 质量面 n≥3 ③ 遥测直写路径并发用例 ④ 全量 n≥10 重复跑取证 ⑤ ⑧挂载轴的**行为腿**治因 (输出变长从哪里来: 台账文案诱因 or 上下文长度) ⑥ MCP 仍需用户改立场才谈得上。

### R503 (2026-09-17) — 题集扩面 v3 (游戏族 1→2 / 见证族 2→3) + 守卫**归因穷举** + 冻结行重钉裁定

> 轮号说明: R499–R502 的轮志落在 `docs/reports/r500-paraphrase-channel-deadcode-rootcause.md` 与 `eval/rover/r50x/README.md` (本台账未逐轮追记)。

- 因果链: R502 主线首跑 (6 题) 两面 6/6 全对, 但**游戏族只 1 个** ⇒ 主线「随机**游戏**」面覆盖不足, 判据外部效度受限 ⇒ 扩面必然改 `eval/probe/*` (声明器具) ⇒ 门禁立刻报 `R2E_R2F_EXIT=2` (两条冻结行器具哈希与现盘不符) ⇒ 冻结行重审与扩面被绑成同一轮。同时机检 R501 候选③ 的诊断: t8 遥测 `src_len=612 / msg_len=5` ⇒ 本地输出是 5 字反问, **长度带同样必拒**, 且本地提示第 4 条本就禁问号 ⇒ 「②误拒」**不成立** (真实病因 = 引擎退化 + 守卫 fail-fast 只报先撞上的一条)。
- 产出①(扩面, 纯增量): `eval/probe/tasks.py` 新游戏族 `sub_game` (减法博弈: `ref`=正推 DP / `check`=记忆化递归极小极大, **双路径必一致才发题**; 输入 `n k` + 允许步集, **保证含 1** ⇒ 无死局无和棋; 输出**数值最小**必胜首取数或 `LOSE` ⇒ 唯一解可字节判分) + 新见证族 `witness_mod_inverse` (`ref`=朴素扫描 / `check`=`pow(a,-1,p)`); `grade.py` 新 `mod_inverse` 判定分支; `run_probe.py` 新 `REF_SRC["sub_game"]` + 负控 `mutation:sub_greedy` (恒取最大)。
- 产出②(链): `src/agent.modelqueue/LocalParaphraseChannel.cs` 的 `Guard()` 由**逐条 fail-fast** 改**逐条穷举归因** (前置不可判项 `source_empty`/`empty_output` 仍单条早返; ②③④⑤⑥⑦ 破几条报几条, 固定序, 名+界值 ≤2 项/条)。**接受/拒绝集合逐位不变** ⇒ 对 token/远端调用数中性, 价值 = 归因可核 (R494「真值必枚举全部 Emit 点」同款)。
- 读数 (首跑前, 全部机检):
  - 自检三连: `tasks.py --selftest` **53/53** (45→53) · `grade.py --selftest` **39/39** (34→39) · `run_probe.py --selftest` **31/31** (29→31); 每条跑 2 次 rc=0。
  - 冻结题集 v3 (`eval/rover/r503/taskset-r503.json`, 逐族定向 dump 机合并): **8 题** = 5 程序族 (`life_k`/`sub_game`/`topo_min`/`vm_run`/`json_mini`) + 3 见证族 (+`witness_mod_inverse`); file sha256 `3e648f5b2ee9…`, 探针口径 sha `929a88e1b02cdccf`; oracle 正控 **70/70 = 1.0000** (新族 `sub_game` 12/12、`witness_mod_inverse` 1/1)。
  - 负控 `nc_r503.sh` 总判 OK: NC1 `json_loose` 整题 0 · NC1b `life_wrap` 整题 0 · **NC1c `sub_game` 恒取最大 整题 0** (用例级 0.2083 仅参考 —— 贪心多数局面与最优手同值, 判红**必须取整题**, 与 R502 口径对齐) · NC2 缺侧 rc=3 · NC3 三态 {0,1,3,0} · NC4 solver 6/6 · NC5 dry-run rc=0。
  - **真机对照 (同窗, rc=0, H1–H5 全 PASS, 同输入 sha `929a88e1b02cdccf`)**: 整题全对 **codex 8/8** vs **本侧 7/8** (差在 `vm_run` partial 8/12); 用量分列 codex `15 调用 / 107,155 tok / 111.5 s` vs 本侧 `15 调用 / 71,233 tok / 32.45 s` ⇒ **tokens −33.5%** (达标 ≥30%), **调用数 15:15 = 平** (R502 是 14:10)。同模型机检两侧落盘 `deepseek-chat`。
- 产出③(门禁/重钉裁定): `eval/rover/r503/ruling_r503_repin.py` (定向 `--only` · 保盘格式 · 幂等 · 改前打印 diff 计划) 重钉两条冻结行 3 字段 —— `probe.randomized-selfcheck`: `tasks.py 32815065ff7a→9c8f09e3ff8f`, 证据**重生成** `probe_selfcheck_evidence.json 00a88bf4cba1→0cdf31bdb101` (P1–P8 全绿, 三阶段 `[[53,53],[39,39],[31,31]]`, 产物内 `provenance.instrument_sha12` 自证一致), `audited_by_round R502→R503`; `r433.probe-code-source-artifact-channel`: `grade.py ef0a81d495ee→21a33eaeb660`, 历史归档 md **不重生成** (声明缺口), `EXP1-Q34→R503`。正控 `bind_evidence --check` ⇒ `R2E_R2F_EXIT=0` 且 `VerificationFormTests` **7/7** (改前 1 failed); 负控 N1 scratch 钉假 sha `deadbeefcafe` ⇒ 门禁报 2 条 VIOLATION (含产物自证冲突) · N2 同副本真值重钉 ⇒ 仅余未重钉行 (按行定位不误伤)。
- 测试/AOT: R498 改写通道类 **33/33** (含新增回归 `守卫_归因必须穷举_R501_t8_实证形状`: 612 字原文 / 5 字反问 ⇒ 须同时报 `question_mark`+`identifier_lost`+`length_band`; 附单条违规仍须单名对照) · AOT `/tmp/pub_r503/agenthost` = **15,409,088 B** / sha256 `0431c3da97a4cc88…` / **IL 类警告 0** (`warning IL####` 计数 0; 非 IL 的 NU1510/CS8625 属存量)。
- 自抓 (3 处, 全部留痕): ① 新族负控初版断言写成**用例级** `rate==0` ⇒ 假红 (实测 0.2083) ⇒ 改**整题** `whole_ok==0` 并注明口径 (不放松判据, 是口径归一); ② `ruling` 器具初版把「字段未改变」一律判失败 ⇒ 合法 no-op (`instrument` 路径字段 / 行2 归档 sha) 被误判 ⇒ 改「仅当声明值≠新值却未写进才红」; ③ 复制 r502 工具时 `AGENT_BIN` 默认值写的是 `pub_r501` (子串替换够不到) ⇒ 改 `pub_r503`, 并在预注册里机取 9 件哈希复核 (`UNIFORM`)。
- 诚实边界: ① 本轮 **7/8 vs 8/8** 是**单样本单窗** ⇒ 不足以断言本侧质量退化, 需 n≥3 复跑; ② 调用数**未下降** (15:15) ⇒ 「判据②远端调用数↓」本轮**不成立**, 只有 token −33.5% 成立; ③ C2 对 token/调用数**贡献 0** (中性), 不得计入任何增益; ④ 引擎退化 (612→5 字) **未修**, 只做了归因穷举; ⑤ 行 2 证据面仍是**历史归档**(未重生成, 已声明); ⑥ 质量面 n≥3 / 遥测 `Emit` 直写并发 / 全量 n≥10 均**未做**。
- 下轮候选 (R504): ① (主线) 题集 v4 扩到 10 题: 增 `nim_multi`/`wythoff` (游戏族 3) + `witness_crt` ② `vm_run` partial 的 n≥3 复跑归因 (摆动还是真退化) + 质量面 n≥3 ③ 本地引擎长原文 (≥600 字) 退化率扫描 (`eval/capability/*`) ④ r433 可重放夹具 (让行 2 证据面可重生成) ⑤ MCP 链级 E2E 仍需用户改立场 ⑥ 全量 n≥10。


## R504 (2026-09-17, 全候选并轮)
- ① 题集 v4 → **11 题** (程序族 7: +`nim_multi`/`wythoff`; 见证族 4: +`witness_crt`), 冻结 oracle 正控 **97/97=1.0000**; 新族负控**整题 0/2** (用例级 0.25 / 0.154 — 口径=整题, 不放松); 仪器自检 53/39/31 ⇒ **61/48/37**。
- **真机同窗对照** (同环境同输入同模型, 11 题): codex-cli `21 调用 · 144,168/8,281 · 152,449 tok` vs 本侧 AOT `17 · 86,755/8,047 · 94,802 tok` ⇒ **tokens −37.8%** / **调用数 −19.0%**; 整题全对 codex **11/11** vs 本侧 **10/11** (唯一失手 p004 `wythoff` 10/13); judge rc=0, H1–H6 全 PASS。
- **器具改后重审 (R2e, 本轮由全量单测真实抓出)**: 首轮 1633/1634, 红项 = `VerificationFormTests.Registry_Exists_And_HasNoViolations` (两条冻结行器具绑定失配) ⇒ 证据面**重生成** (q28: 53/39/31→61/48/37, artifact `0cdf31bdb101`→`0f16d271c894`, instrument `2dba8418221c`) + `decl_sweep.py --apply` (2 漂移→0) + `ruling_r504_repin.py --apply --only` 定向重钉 2 行 (行 658/660/662/1518/1520) + 门禁 `bind_evidence.py --check` **0 VIOLATION / R2E_R2F_EXIT=0** + 负控 (假 sha) 门禁红且点名 ⇒ 修后 **1634/1634 × 10 连跑全绿**。
- **候选② `vm_run` 归因**: 冻结 vm_run 题集 (2 题/23 用例) **6 臂** 全 2/2 整题、23/23 用例 + 主窗 12/12 ⇒ R503 partial **不复现** (n=7 观测 0 次) ⇒ 判为单样本摆动。
- **候选④ r433 行证据面可重放**: `replay_r433_face.py` 重放冻结 9 行 ⇒ 复现 **8 行 drift=0**, 缺口 1 行 (`probe-m6-agent.json` 不在行内 glob `*r433*` 内) ⇒ `PASS_DECLARED_GAP` (缺口已声明, 未闭合)。
- **AOT**: rc=0, **IL 警告 0** (CS 6 为既有), 15,409,088 B, sha256 `dcb747e873645084adc5c560cab24382a54836a49ef9312c42ada4ccfcdbb57c`。
- 诚实边界: ③ 本地 3B 长原文 (≥600 字) 退化率**未测到** (起手闸连续 2 PASS 未过 ⇒ fail-closed rc=3, **无读数**); 判据② 未达 −30%; 全 11 题质量面仍 **n=1**; ④ 缺口 1 行未闭合; ② 的 6 臂只覆盖 vm_run 单族。
- 下轮候选 (R505): ① (主线) 题集 v4 上**质量面 n≥3** 同窗对照 ② 判据② 攻坚 (17→≤14 调用: 逐题列调用构成) ③ 本地引擎长原文退化率 (须先起 llama-server + 起手闸 2 PASS, 否则继续 fail-closed) ④ 行 2 重放缺口闭合 ⑤ MCP 链级 E2E (需用户改立场, 排除项)。


## R505 (2026-09-17, 全候选并轮: 器具修复 + 质量面 n≥3 + 判据② 逐题构成)
- **机检抓出的 R504 缺陷（本轮首要产出）**: R504 判分输入是 /tmp **活目录** (`$D/adapter`), 而 adapter 落盘名 `side-<side>-<NNN>.json` 里的 NNN 是**进程内计数器**; 判分之后 `cand2_vmrun_n3.sh` 复用同一 `DEMO_OUT` 又起了一个 adapter ⇒ 计数从 001 重开 ⇒ **覆盖**已被判分的 9 个文件 (`side-agent-001..009`)。取证: `eval/rover/r504/evidence/adapter-usage.txt`（判分时冻结）与现盘逐文件比对, 9 行 in/out 全部不符（例: 001 `6521/337`→`6074/922`; 002 `1496/349`→`6064/570`; 003 `6410/356`→`1790/611`）。R504 读数（17 调用 · 94,802 tok）在**判分当时**成立, 但**现已不可重放** ⇒ 记为「读数成立、证据不可重放」。
- **修复三处（均配首跑前负控, `eval/rover/r505/evidence/nc-r505.json` 13 块全 PASS）**: ① 命名空间守卫（目标目录/证据目录非空 ⇒ rc=4 **且不启动任何作业**, 负控 nc1g 两端）; ② 判分只读**仓内不可变快照** + 逐文件 sha256 冻结清单 ⇒ 判分成为快照的纯函数（可无限次重判, 无需重跑 LLM）; ③ 污染检出器 `check_usage_replay.py`（冻结清单 vs 目录, 失配 rc=2 并**点名文件**; 负控 nc11 两端: R504 实况红且点名 9 文件 / 干净副本绿 / 注入 1 处即点名 1 处）。
- **主线对照 n=3 批（同题集 11 题 · 同环境 · 同模型 · 同 adapter · 同 AOT 二进制）**: a `25 调用 · 177,172 tok` vs 本侧 `21 · 127,623`（质量 10/11 vs 10/11）; b `33 · 270,552` vs `18 · 101,415`（9/11 vs **11/11**）; c `22 · 154,943` vs `19 · 80,551`（**11/11** vs 10/11）。
- **H7 质量面 (n=3)**: 本侧 **31/33** vs 外部真值 **30/33**, 逐题 mode 逐批一致 28/33 ⇒ **质量不降**（PASS）。**token 面**: 同窗 本侧/真值 = 0.720 / 0.375 / 0.520（均值 0.538）⇒ 同题同窗下**本侧 token −46%**。
- **H8 判据②**: 本侧每轮调用 **21/18/19**（均值 19.3）⇒ 目标 ≤14 **未达标**（诚实记）。三批**逐题调用构成**合计: `p001 10 · p002 10 · p004 9 · m001 5 · p006 5 · p007 4 · m002/m003/m004/p003/p005 各 3` ⇒ **三处热点占 55%**（工具轮 + 修正轮 + 微步骤隔离问询）——这就是下轮压缩的靶点。
- **器具改版留痕（判分/归因器 v2→v3c）**: 批 C 出现 `[微步骤隔离问询]` 前缀与题面**片段**问询, 归因器新增「标记剥离 + 反向包含 + 片段命中 + 同轮延续」; 因判分与快照分离, 全部**快照重判**（不重跑 LLM）, 影响面机检: 三批的**冻结判据/用量/质量表逐位不变**, 仅 H8 红转绿（批 C rc 1→0）⇒ `amendments[v2, v3c]` + `judge-amendment-*-impact.json`。
- **自抓 2 处（全部留痕）**: ① 重判驱动脚本**猜**探针产物名 ⇒ judge rc=3 fail-closed, 脚本却仍拿旧 verdict 比较并报「冻结判据不变」= **假绿** ⇒ 修: glob 解析 + 判分须自报完成标记并落独立临时件（判分器是确定性纯函数, 产出可与旧件逐字节相同 ⇒ **禁用「内容变化」判新鲜度**）; ② 归因器初版对「同长度多题命中」会**静默挑一个** ⇒ 改 fail-closed（tid=None 交第二阶段）。
- **AOT**: 本轮**未改链代码** ⇒ 复用 R504 二进制（预注册钉 sha256 `dcb747e8…`, 15,409,088 B）⇒ 同环境可比。
- 诚实边界: ① 目标 ≤14 调用**未达标**; ② 本地引擎长原文退化率**仍未测到**（起手闸未过 ⇒ fail-closed, 无读数）; ③ r433 行 2 缺口: **证据面已闭合**（9/9 行漂移 0）, 但登记行状态未更新; ④ MCP 链级 E2E **排除项未动**; ⑤ 与 R504 本侧读数（17 · 94,802）**禁相减**（不同批次/窗/题集规模）⇒ 不给「较上轮」结论; ⑥ 真值侧调用数本身在 22–33 间摆动 ⇒ codex 不是常量基线。
- **候选④ 行 2 重放缺口闭合（本轮完成）**: `eval/rover/r505/replay_r433_declared.py` 改为**逐字执行行内声明的命令**（含 `--run data/probe/probe-m6-agent.json`）⇒ 复现 **9/9 行、漂移 0**; 前态负控（R504 老夹具那一版, 只有 `--glob`）⇒ **8 行, 恰好缺 `probe-m6-agent.json` 那一行** ⇒ 闭合非空心（`evidence/replay-r433-closure-r505.json`）。**未做**: `docs/verification-registry.json` 该行状态仍写 `PASS_DECLARED_GAP`（改登记行须连带跑 `bind_evidence.py --check` 形式门禁 ⇒ 留给 R506, 闭合证据已落盘）。
- 下轮候选 (R506): ① (主线) 压热点 `p001/p002/p004` 的工具轮与修正轮（19.3 → ≤14 调用且质量不掉）② 本地引擎长原文退化率（起 llama-server + 起手闸 2 PASS, 否则继续 fail-closed）③ 登记行状态更新 + `bind_evidence` 门禁（④ 的收尾）④ 全量 n≥10 ⑤ MCP（排除项, 需用户改立场）。

## R512 (2026-09-17, 全候选并轮: 外部真值对照 p3+p4 两侧 n=2 + 预注册增补臂 B)
- **主线对照 (同环境·同输入·同模型 deepseek-chat)**: 臂 A=本侧 agent 默认预算 ×2 / B=本侧 agent 预算 12 ×2 (预注册增补, B 起臂前落盘 `prereg-r512-addendum.json`) / C=codex-cli ×2; 起手闸 2×PASS; 每跑次独立 session; 14 项器具哈希 + 5 判据预注册 (起臂前)。
- **机检判据**: C1 同环境/同输入/同模型 PASS; C2 质量不降 PASS; C3 token ≤0.70×codex **PASS** (max 0.6165); C4 调用 ≤codex **PASS** (max 0.5714); **C5 铁律11 FAIL** (`exec_precondition --round R512` rc=1, 阻塞行 = p4 全 6 行) ⇒ 本轮 token/调用降幅一律标「参考 (未可验收)」。
- **p3 (有区分力子集)**: 两侧全 12/12; 本侧 4–14 调用 / 60,449–263,437 tok vs codex 43–46 调用 / 849,925–1,266,833 tok ⇒ 调用 ↓87–91% / token ↓89–95% (仅参考)。
- **机检定位的夹具缺陷 (本轮首要产出)**: p4 题面第 2 条只写「全局选项 `--now` 注入当前时间」, **未写缺省语义**; 隐藏用例 8/12 条不带 `--now` 调用 ⇒ 三臂 (agentA/agentB/codex) 失败集合**逐字相同** (4/12), 外部真值同样失败 ⇒ 判据丧失区分力。复现: `python3 -B -m tasksvc.cli --db /tmp/t1.json add 买菜` → rc=2 `bad_request`; 加 `--now 1000` → rc=0。旁证: R511 入册行负控已写「忽略 `--now` ⇒ 11/12 红」, 当时未按夹具缺陷处理。
- **判据器负控 (SELFTEST=OK, `evidence/nc-r512.json`)**: 正控 p3/p4 各 12/12 (只对副本判分) + 6 变异体全检出 (p3 三个沿用 R508 原串; p4 三个: 原地重写 ⇒ 精确点名 `no_temp_residue`; id 复用 ⇒ `id_monotonic_no_reuse`+4; ttl 失效 ⇒ `ttl_expiry_uses_injected_clock`+2)。**自抓**: 首跑报 NC_NOT_DETECTED 系我方预期用例名口径写错 (用例名不带 `test_` 前缀), 修正后转 OK ⇒ 负控对本轮判据口径有效。
- **AOT**: 本轮**未改链代码** ⇒ 复用 R511 二进制 `/tmp/pub_r511/agenthost` ⇒ 同环境可比 (未重发布)。
- **诚实边界**: C5 未过 ⇒ 降幅不作验收依据; B 臂为事后增补 (不作主验收依据); B 臂 3 次中止/作废尝试的 agent 侧 dump 区段 **29–58** 已显式排除 (`evidence/excluded-dumps-r512.json`); nc 首跑把 `_grade.json` 落在参考解树 (1406/1292 B) 已删除并改为只判副本; 未测 p1/p2/p5、预算曲线。
- 下轮候选 (R513): ① p4 题面 v2 (写明 `--now` 缺省 = 系统时钟) + 两侧 n=2 重测 ⇒ 争 C5 rc=0 ② 题面-判据一致性**机检器** (逐条用例断言找题面依据句) ③ p1/p2/p5 纳入 ④ 预算曲线 6/9/12/16 × n≥3。


## R513 (2026-09-17, 同 tick 内续跑: p4 题面 v2 修订后重测 ⇒ 铁律 11 rc=0)
- **最小修法**: 题面 v2 增补「未提供 `--now` 时必须回落到系统时钟 (time.time()), 不得报错、不得要求该选项必填」; **隐藏用例与参考解逐字节不变** (用例 sha `9105a116…` 两侧同; `diff -r` 参考解树为空; v1 `678624f5…` → v2 `384fa721…`), 由 `build_taskset_r513.py --check` 自检 rc=0。
- **重测读数 (预注册 + 起手闸 2×PASS + 每跑次独立 session)**: 四跑次**全部 12/12 整题全对**; 铁律 11 前置 `exec_precondition --round R513` **rc=0** (`ACCEPTABLE_SCOPED=True`, `SELF_REPORT_AGREES=True`) ⇒ 本窗读数**可作验收依据**。
- **判据机检**: C1/C2/C4/C5 PASS, **C3 FAIL** —— w1 token 比 0.5719 (↓43% 达标) / w2 比 1.1376 (该跑次 codex 仅 78,814 tok / 8 调用, 少于本侧 89,660 / 7)。⇒ **可稳定验收的是远端调用数下降** (7 vs 14 / 8; 比 0.50–0.875), 「token ↓≥30%」在本任务上**不是稳定结论** (codex 侧用量跨跑次 2 倍级摆动)。
- **v1→v2 同题对照**: v1 三臂全 4/12 (失败集合逐字相同) → v2 四跑次全 12/12 ⇒ 归因于**题面缺省缺失**, 而非任一实现侧能力。
- **诚实边界**: C3 未过 ⇒ token 降幅不作结论; n=2 / 单任务; B 臂未纳入 R513 (R512 已示默认预算在 p3 上即 12/12); R512 与 R513 窗口**禁相减** (题面版本不同)。
- 下轮候选 (R514): ① token 判据稳健化 (改以「不必要的远端调用数下降」为主判据; token 取多跑次中位数 n≥5 并预声明 codex 侧波动为噪声源) ② 题面-判据一致性机检器 ③ p1/p2/p5 纳入 + 预算曲线 ④ 第二外部参照 (除 codex-cli)。

---

## R516 (2026-09-17) — 编排节点「成功」绑定磁盘证据 + 写范围契约 (轮志: `docs/reports/r516-node-artifact-scope-contract.md`)

- **问题 (R515 现场)**: 节点 `Completed` 可以**零产物** (n3 5 ms / n4 178 ms, 归档 `eval/rover/r515/evidence/report-orch-v2-12step.json`); 文件范围只写在提示词里 = 软约束, 越界写无任何拦阻; 同层两写者互相覆盖只能靠人工看提示词发现。
- **改进**: ① 逐节点快照差**上收到编排器** (单一权威源), 宿主侧同名实现删除; ② `--scope` 范围契约文件 (尾部 `/` 目录前缀 / `*` 前缀通配 / **段边界**判定) ⇒ 违反即 `Failed` 并**点名路径** (越界 / 零范围内增改 = 假绿防护); ③ **同层范围重叠在建立 agent 之前拒收** (rc=2, 零 LLM 调用)。
- **真机证据**: 5 臂 6 判据全绿 (`eval/rover/r516/evidence/verdict.json`): 前态无机制 / 前态锚 / 零产物⇒Failed / 真干活⇒Completed 不误杀 / 越界⇒Failed 点名 / 重叠⇒rc=2 且 adapter 调用 0 增量 ⇒ 定级 **L3**。
- **费用面**: 负控臂**零 token**; 本轮全窗 24 次调用 / 55,928 tokens (标「参考 (未可验收)」—— 前置闸 rc=3, 无对照题集)。
- **诚实边界**: 同层并发窗内**不作快照差归属唯一性**宣称; 多层并发未真机跑; token ↓≥30% 判据本轮无读数。
- **结转 (未静默丢失)**: R514/R515 **未**落 `improvements.md` 轮节 (R514 只落 master plan + 计划文档, R515 只落轮志); R404–R407 回填仍缺。


## R518 (2026-09-17) — 编排节点预算自适应 + 生成器契约负控 + 双包规模面对照 (轮志: `docs/reports/r518-mainline-scale-arm-and-node-budget-escalation.md`)

- **② 节点预算自适应 (链代码)**: 远端节点仅因「零产物」判 Failed 时自动翻倍重试 (上限 32 步 / 次数 0..3, **缺省 0 = 旧行为逐字不动**); 越界与异常**不**升预算 (不掩盖真失败); 遥测/报告新增 `budget_steps`/`escalations`/`attempts`/`budget_ceiling_effective`/`node_escalations_max`/`escalations_total`。**真机 liveness**: n3 `['6:Failed','12:Completed']` ⇒ 该次重试直接决定了 tasksvc 整包 12/12; 运行级预算上界 24→36。
- **②′ 运行期缓存排除 (同轮真机自抓的链缺陷)**: 节点按题面「写自测并运行」⇒ 解释器自动落 `__pycache__/*.pyc` ⇒ 旧快照差判其越界 ⇒ 整链 fail-closed (真实产物 cli.py 尚未写就被判死)。现只排除字节码/缓存 (段名 `__pycache__`/`.pytest_cache`/`.mypy_cache`/`.ruff_cache`, 后缀 `.pyc`/`.pyo`); 源码/数据照旧入范围契约。
- **③ 契约机检器 (修 R517 事故)**: 计划/范围双源机检 —— 镜像判据 (P1-P10/S1-S8/H1) + **生成器生成即机检非法不落盘** + 落盘回读 + 起臂前 `--check` 硬前门; 夹具保真闸 (节点文本须以题面原文结尾, 含 `|`) 禁偷改题面。**负控 12 变异 × 双源全绿** (镜像报红 ∧ AOT 二进制校验期 rc=2 拒收), 含事故本体「范围重复声明」; 变异有效性自检防 NC 空转。
- **① 双包规模面三臂 (窗口 w2)**: A 本侧单轮 **24/24** 用例 / **13** 调用 / **143,206** tok / 51.9 s vs C codex 21/24 / **36** 调用 / **501,207** tok / 128.7 s ⇒ 调用 **↓63.9%** · total token **↓71.4%** (R413 阈值 30% 两量均达标); O 编排臂 7 节点 6/7 完成, tasksvc **12/12**、kvsvc 0/12 (q1 两次零产物)。
- **规模面结论 (反 R515 假设)**: 本侧**单轮**默认预算已覆盖双包 24 用例 ⇒ 「双包超出单轮硬顶」在此规模**不成立**; 编排器必要性本轮**未被证明** (其价值转为「预算自适应用于救回单节点」)。
- **铁律 11 前置器**: `exec_precondition --round R518` **rc=1** ⇒ 上述降幅**一律标「参考(未可验收)」** (要求面 w2/agentA 24/24 ✓ 但 w2/codex p3 仅 9/12 ✗)。
- **诚实边界**: ① reps=1 且**外部真值跨跑次方差显著** (同一 p3: w1 12/12 → w2 9/12) ⇒ 对比不作验收依据; ② **w1 整窗作废** (留痕不删): 臂 A 未 `export AGENTFRAMEWORK_CONFIG` ⇒ 绕过计量 adapter (未计量真实调用已发生) + 编排臂 `cwd` 落在节点工作区内 ⇒ 宿主自写 `data/**` 被判越界; 两条器具缺陷当轮修 (含范围模式语法 `w2/agentA/*`→`w2/agentA`); ③ 编排臂 token 禁与单轮臂混算 (输入粒度不同); ④ 单测 1722/1722 · AOT 0 IL 警告 (15,605,072 B, sha12 `6ac91728e1b4`)。
- **结转 (未静默丢失)**: `improvements.md` **R517 轮节仍缺** (前一轮遗留, 不代写); R404-R407 回填仍缺。
- **下轮候选 (R519)**: ① 对比读数稳健化 (主判据取「远端调用数下降」+ reps≥3, 预声明 codex 侧波动为噪声源) ② q1 零产物定因 (分段切分/提示词 vs 预算; 试 `--node-escalations 2`) ③ 契约机检接入所有轮脚本 (硬前门) ④ R517/R404-R407 轮节回填 ⑤ 编排并行窗归属唯一性真机验证。

## R521 (2026-09-17) — 游戏类长任务三臂同窗 (w2) + 器具两缺陷自查修复 (轮志: `eval/rover/r521/REPORT-r521.md`)

- **主线三臂同窗读数** (`games-longtask-v1` 58 用例 · 同 adapter 窗口 w2 · 双侧 `deepseek-chat`): **A 本侧单轮 58/58** (19 上游调用 / 302,809 tok / 66.1 s) · **C codex 外部真值 58/58** (5 调用 / 46,372 tok) · O 编排 5 节点×8 步 **31/58** (30 调用 / 429,908 tok)。⇒ 质量面 A=C **打平**; 效率面本侧 = codex 的 **6.53×** tok ⇒ **不比外部真值省**; R413 的 token ↓≥30% 本轮**无同窗关闸臂 ⇒ 未测, 不宣称降幅**。
- **器具缺陷 1 (起臂面)**: 臂 A 走 `proj_run_side --side agent` **未传 `--max-steps`** ⇒ 工具面关闭 ⇒ CLI 退回纯对话: 1 调用 / 5.4 s / **零产物** ⇒ 该窗 (w1) 整窗作废, 证据归档 `eval/rover/r521/nc/w1-armA-no-steps/` (含 C 58/58 · O 9/58 仍有效读数); 修: `--max-steps 32` + 起臂后产物非空断言。
- **器具缺陷 2 (冻结面, 假绿)**: 空产物树被**静默跳过** ⇒ `snapshots/<win>/agentA` 不落盘 ⇒ 前置器只遍历已存在目录 ⇒ **rc=0 假绿** (w1 实测)。修: `emit()` 先 `makedirs` ⇒ 空臂也落盘 (`snapshot_empty: true`); **负控面板** `eval/rover/r521nc/` (空树 + 自报 `all_pass=true`) ⇒ **rc=1** · `BLOCKED w1/agentA/g1 0/58` · `SELF_REPORT_AGREES=False`。
- **候选② 编排臂 9→31/58 逐用例定因**: 5 模块**都在盘上** ⇒ 失败面是**接口契约**非算法: life 输出字母表 `0/1` (应 `./#`) 0/14 · sub 首行未跳过 ⇒ IndexError 0/14 · nim 取法非规范最小解 5/15 · wythoff `WIN` 后丢两整数 4/15 (`eval/rover/r521/diag-orch-r521.md`)。**摆动**: 同器具同题面 O 在 w1=9/58、w2=31/58 ⇒ 单次读数禁作能力结论。
- **候选④ 闭合 (机检)**: `eval/capability/r518/scan_round_sections.py` ⇒ `C1 MISSING n=0 · C2 ZONE_ORDER n=0 · SCAN_EXIT=0` (R404–R407 缺口已由 R518 器具闭合) · R517 轮志在位 · R521 轮节本轮补入。
- **铁律 11 前置器**: `exec_precondition.py --round r521` ⇒ **rc=1** (`ACCEPTABLE_SCOPED=False` · `SELF_REPORT_AGREES=True`): 预注册 `evidence_scope` 写 `w1/*`, 该窗被缺陷 1 作废 ⇒ 验收窗 `w2/agentO` 未声明 ⇒ fail-closed; 事后重钉件 `scope-posthoc-r521.json` 明标 `SCOPE_POSTHOC=1` ⇒ 仍 rc=1、不得当验收依据 ⇒ **本轮未达可验收, 全部读数标「参考 (未可验收)」**。
- **诚实边界**: ① R413 判据无读数; ② 6.53× 为跨实现方向读数 (非同源消融); ③ 编排 31/58 单次; ④ 本轮**零产品源码改动** ⇒ 未重发布 AOT / 未跑单测; ⑤ w1 作废系**器具**缺陷非产品缺陷 (产品面在 w2 按预期工作)。
- **下轮候选 (R522)**: ① (主线/R413) **同窗关闸单变量消融臂** ② 编排节点内置逐模块 I/O 契约自测 (承候选②定因) ③ 编排摆动 n≥3 量化出区间 ④ `evidence_scope` 支持窗口无关模式 (`*/agentO`) ⑤ 回执回显落点 (待 token 数据裁定)。

## R522 (2026-09-17) — 动作环上下文纪律: 同窗单变量消融 (结果: 无增益, 如实收窄) (轮志: `docs/reports/r522-action-loop-context-discipline.md`)

- **靶点**: 用户 2026-09-17 逐字质疑「新算token你仅是上下文用的没codex好」⇒ R521 逐调用定因: 19 调用里 20 步全在自测往返, 回读命令计数 0 ⇒ 病灶 = 验证回路粒度 + 收尾长度, 不是召回。
- **产品改动**: `ActionLoopDiscipline.cs` (验证合并 / 探针不落盘 / 收尾从简), 只注入动作环 system 尾部, 环境轴 `AGENTFRAMEWORK_ACTION_DISCIPLINE` (缺省开); AOT `cc611646…` · IL 0 · 单测 1,733/1,733。
- **读数 (单窗 n=1, 同二进制)**: `A0-off` 56/58 · 4 调用 · 新算 9,075 · completion 3,850 / `A1-on` 58/58 · 4 调用 · 新算 10,128 · completion 4,973 / `C-codex` 58/58 · 5 调用 · 新算 3,775 · 命中 90.8%。
- **裁决**: C2 ✅ / C3 1.00× ❌ / C4 1.116× ❌ / C5 1.292× ❌ ⇒ 不宣称增益; R521 的 19 调用两臂都不复现 ⇒ 主因非纪律, 需 reps≥3。
- **同轮器具修复**: ① `mount_check_r522.py` M4 键缺失假红 ② 前置器 `acceptable_scoped` 绕过 `BLOCKED` 造 rc=0 假绿 (改 rc 前置 blocked 空)。
- **诚实边界**: `--round r522` rc=1 ⇒ 读数标「参考 (未可验收)」; A1 末次调用 = 宿主机器闸门修复回路, 增量不可归因纪律。

## R523 (2026-09-17) — n=3 同窗对照: 纪律无增益 (判为窗口方差) · 本侧不优于外部真值 · 验收面语义收窄 (轮志: `docs/reports/r523-n3-same-window-contrast.md`)

- **主线读数 (三窗 × 三臂, 同二进制 `cc611646…`, 零产品源码改动, 单变量 = 纪律 env)**: `A1-on` 调用 17/4/12 · 新算 prompt 20,004/10,068/13,548 · 用例 58/58/58; `A0-off` 4/8/12 · 6,655/11,069/14,054 · 58/58/58; `C-codex` 7/9/5 · 3,824/6,133/3,506 · 58/**46**/58。
- **裁决 (预注册 C1..C7)**: 中位比 A1/codex 调用 **1.71** · 新算 **3.54** · 有效 token **3.05** · 名义 **2.29** ⇒ 三条降幅判据**全否, 不宣称任何降幅**; 质量面 A1 三窗 58/58 ≥ A0 58/58 ⇒ 未降; A1/A0 调用中位比 **1.50** (4.25/0.50/1.00 符号翻转) ⇒ **R522「19→4」是窗口方差** (同臂跨同输入窗摆动 4.25 倍), 纪律**无增益**。
- **外部真值不稳定 (机检)**: codex 三窗 58/**46**/58 ⇒ 单窗交叉对比无判别力; 后续轮必报逐窗读数 + 极差。
- **器具 (验收面语义修复, 预注册 line 66)**: rc 改读 `blocked_scoped` (require ∪ 未声明), 早退分支经 `_early_scope()` 同规则, 全局 `blocked` 仍全量记账; **7 项正/负控**: 仅 NC2/NC6 (非验收面失败) 1→0, NC1/NC3/NC4/NC5/NC7 恒 1 ⇒ 未放水; 旧轮 rc 不变 (r521=1, r522=1); R523 本体 rc 仍 1 ⇒ 修复非为本轮开绿灯。
- **诚实边界**: 铁律 11 rc=1 ⇒ 全部读数标「参考 (未可验收)」; 单题族 (games-longtask-v1) · 数学/程序题族未测 · cached 价差未计入宣称。
- **下轮候选 (R524)**: ① 步数/调用数是唯一杠杆 (中位 12 vs codex 5) ⇒ 一次计划→批量执行 / 工具面合并; 步数入 KPI 主列 ② n≥5 + codex 失败窗 `unreliable` 判据化 ③ 纪律缺省位裁决 (`off` 或降级纯提示) ④ `evidence_scope.nonrequired` 写入轮模板。

## R524 (2026-09-17) — 提示词前缀纪律: 常量前置 + 易变后置 + 自指遥测闸 (结果: 结构修复成立, 质量未证) (轮志: `docs/reports/r524-*` · prereg `eval/rover/r524/prereg-r524.json` v2)

- **靶点**: 用户逐字「那说明你做错了啊，肯定要命中常亮前沿在后面加的，你往中间塞东西了？」+「上下文几乎不涨才是对的」⇒ 逐字节定位: 四份 system 前 4,477 字符相同, 分叉点 = `[工作区文件 data/activity/<pid>.json]`, 后 757 字符每轮重算。
- **产品改动**: `SessionInjectionPlanner.cs`(静态段白名单移出「工作区文件」) · `ContextAssembler.cs`(工作区自动召回缺省关 + 自指遥测路径闸) · `ActionLoop.cs`(`ToolResultCharCap`) · `ActionLoopDiscipline.cs`(3→5 条: 零过渡叙述/回执按需取全文) · `R524PrefixStabilityTests.cs`。
- **读数 (三窗 v2, 同二进制 `7c5b59ef…`)**: M1 常量 system ✅×3 · M2 无遥测 ✅×3 · M3 首调用新算 5,372→**343–349** ✅ · M4 步间涨幅 495–504 (codex 同档 411–444) ✅ · M5 中位回执 413/341/— (2/3 窗) · M6 ❌×3(`[技能知识参考]` 仍在 user 轮)。质量 A1-on 51/58·58/58·58/58; A0-off 0/58·0/58·46/58(双峰)。
- **裁决**: 结构修成立 (前缀不再漂移、首调用新算降 15×); **M6 未过** ⇒ v2 不宣称达标, 缺口定因 = 材料块硬编码进 user 轮 (`IndustrialAgentV2.cs:1308`) 绕过白名单 ⇒ 交 R525 修。
- **诚实边界**: M3/M4 为 R524 预注册阈值; w1 质量 51/58 单窗不作结论; A0-off 双峰 ⇒ 纪律文本是工具面对齐的必要条件之一。

## R525 (2026-09-17) — 提示词分区常量前缀重构 (外部真值 Fable 5.1 结构对齐 · 铁律 12 入宪) (轮志: `docs/reports/r525-prompt-partition-prefix.md`)

- **靶点**: 用户令「根据它的提示词重构我们当前 agent 系统, 并记入铁律」; 外部真值 = Fable 5.1 泄露 system (自测 274,608 字符 / 270 段 / 46 工具 schema / 一个逐字节恒定前缀)。
- **产品改动**: `SessionBaseline.cs` 重写 Compose ⇒ **§1..§11 命名常量分区**(新增 §3 记忆与召回规则 / §7 技能菜单与按需加载; 修原编号跳七); `IndustrialAgentV2.cs` 把 `[技能知识参考]` 焊进首轮冻结常量前缀 (修 R524 M6 缺口); `R525PartitionStructureTests.cs`(7 例结构锁); `eval/rover/r525/structure_check_r525.py`(M1–M6 + S1–S5); 铁律 12 入宪。
- **读数 (三窗, AOT `1e25edd6…` 15,617,360 B)**: 处理臂 system **9,803 字符 / 11 段 / 跨三窗同 sha `6910b5eb`** ⇒ S1/S2 ✅; M6 **✅×3**(材料已在常量前缀) · M2 ✅×3 · M5 ✅×3 · M1 ✅×3 · M3 ✅ w2/w3 (暖启新算 **354/359**; w1 冷启 2,582 判否) · M4 ✅ w1/w3 (w2 709.5 vs 700 判否) · S3/S4/S5 ✅×3。质量: w1/w2 **三臂全 58/58**; w3 两侧 agent 臂 **0/58** 而 codex 58/58 (`PRECOND_RC=1`)。
- **裁决**: **结构对齐目标达成且机检通过** (常量前缀 + 只追加 + 段序恒定 + 技能材料前置); **能力增益未证** ⇒ 只宣称结构与 token 形状对齐。铁律 12 生效。
- **器具**: ① 机检器新增 aux 调用剔除 (宿主修复回路, 原判定保留) ② S3 段体量上界取外部真值 (10,784→12,000) ③ 两处后验已在 prereg `posthoc_notes` 单列。
- **诚实边界**: w3 `PRECOND_RC=1` ⇒ 标「参考 (未可验收)」; A0-off 双峰不构成有效对照臂; 调用数摆动 5–32 (本侧) / 6–22 (codex) 仍是主不确定源。
- **下轮候选 (R526)**: ① 把「调用数/步数」做成一等问题 (批量执行 + 计划一次成型) ② 冷启窗 (换前缀后首窗) 单列 KPI 口径 ③ 技能菜单从常量前缀动态枚举 (skills/ 目录 → 菜单段) ④ 复现 w3 型「产物不可运行」定因 (life rc=1 逐用例) ⑤ 第二外部真值参照。

## R526 (2026-09-17) — 项目级完全重构 (单类型单文件 · 命名空间归一 · 巨类拆分 · 构建配置集中化) (轮志: `docs/reports/r526-project-refactor.md`)

- **靶点**: 用户令「完全重构当前项目，如果不懂怎么重构，重构是什么的意思入网上搜」。先定义后执行：重构 = **不改外部可见行为、只改内部结构**；判据 = 行为不变（1755 测试 + 构建）∧ 结构不变式成立（机检 + 负控）。
- **产品改动 (机械变换, 每步后构建+测试)**: ① 类型单一化 —— 176 个多类型文件 / 575 个次要类型经 Roslyn 语法树外移为单文件（`tools/refactor/reftool extract`）；② 命名空间归一 —— `agent.Recall*` 61 文件小写化、测试命名空间统一 195 文件、20 个无命名空间文件补齐、`CredentialEncryption.cs` 归位 `agent`（`agent.io` 因 netstandard2.1/LangVersion 8.0 保持块式）；③ 巨类拆分 —— `IndustrialAgentV2` 3204 行 → 主 2263 + Commands 441 + Plan 215 + Context 372（字段/嵌套类型留主文件）；④ 构建配置集中化 —— `src/Directory.Build.props` + 25 csproj 去重；⑤ 容器文件改名 32 个 `<类型名>.cs`。
- **读数**: `src` 文件 475 → **1054**，行 93,828 → 97,045；含 >1 顶层类型文件 **176 → 0**；文件名≠类型名 **33 → 0**；无命名空间文件 **20 → 0**；目录内混命名空间 **4 → 0**；构建 0 错误（每阶段全量 rebuild）；测试 **1755/1755 绿**（+5 结构守卫）；AOT `/tmp/pub_r526/agenthost` 15,617,360 B / sha `6b565aa0…` 可执行冒烟 rc=0（凭据未配置 ⇒ 诚实失败，未伪造）。
- **裁决**: **结构层一次完整闭合** —— 四条不变式全部成立且**可执行**（`RefactorStructureTests` I1/I2/I3a/I3b）；负控面板 4 类注入缺陷全红（判据非恒绿）；铁律 13 入宪（`iteration-master-plan.md §0-0`）。
- **器具**: `tools/refactor/`（Roslyn reftool 四模式 + 不变式机检 + 七步流水线 + README 教训）；登记表 +4 行 / `covers` 修正 36 行；4 处源码路径钉死测试改目录级/片段级扫描（强度不降）。
- **诚实边界**: `agent.core/{userinteraction,subagent}` 20 文件命名空间横跨两程序集**未收敛**（需跨程序集引用重写，逐条豁免锁住 ⇒ R527 候选）；`OnProcessAsync` 1662 行单方法**未拆**（语义变换，非机械重构）；`ModelQueueRouter`/`ContextAssembler`（1530/1513 行）未拆 partial；行数 +3.4% 是单类型单文件的文件头成本，非性能回归；期间 1 次 `FrontendAskSameConnTests` 偶发失败（隔离复跑 2 次 + 全量复跑均过，无因果）。
- **下轮候选 (R527)**: ① `agent.core` 命名空间收敛（Roslyn 语义层改名 + 引用重写）② `OnProcessAsync` 方法级抽取（需等价性夹具）③ `ModelQueueRouter`/`ContextAssembler` partial 拆分 ④ `Directory.Packages.props` 中央包版本 ⑤ 不变式接入「新增文件」前置闸。

## R527 (2026-09-17) — 结构收口: R526 五候选同轮闭合 (ns 收敛 / 巨类拆分 / CPM / 前置闸 / 有界抽取) (轮志: `docs/reports/r527-structural-closure.md`)

- **靶点**: R526 §6 五候选 + 结转遗留**同轮并推**（用户令 2026-09-16 禁单步）；判据预注册 `eval/rover/r527/prereg-r527.json`（先落盘后读数）。
- **产品改动 (每步后构建+全量测试)**: ① 命名空间收敛 —— `src/agent.core/{userinteraction,subagent}` 20 文件声明改 `agent.core`（`tools/refactor/pipeline/09_converge_namespace.py`），`agent.core` 下残留 **0**；引用方 `using` 由**编译器驱动**伴随器补齐（`10_fix_moved_type_usings.py`，fail-closed：只按 CS0246/CS0103/CS0234 报点补 `using`；并修正对**未搬走**类型（`IsolatedTaskRunner`/`ILLMCallerForIsolated`）的误改写）；② `OnProcessAsync` 有界抽取 —— 轮起始清零+心跳 → `BeginTurn()`、reply 因果绑定+偏题状态推进 → `BindReplyAndAdvanceTopicState()`（**方法体 1600 → 1550 行**）；③ `ModelQueueRouter`/`ContextAssembler` partial 拆分（最大分片 **531 行**，源级钉死改 `SourcePin.Text/TextParts` partial-aware 读取）；④ CPM —— `src/Directory.Packages.props` 22 条目接管 41 处 `PackageReference`，内联 `Version=` **0**；⑤ `tools/refactor/new_file_gate.py`（G1..G7）接入**真实生效钩子** `tools/hooks/pre-commit`（`core.hooksPath` 指向，路径改仓根绝对路径）。
- **读数**: 全量测试 **1755/1755 绿**（RC=0）；构建 0 错误；AOT `/tmp/pub_r527/agenthost` **RC=0 · IL 警告 0** · 15,609,168 B（R526 15,617,360 B，**−8,192 B**）· sha `d70a9741…` · 冷启动冒烟 rc=0；等价性夹具 **10 臂逐字节全同**（pre=R526 AOT / post=R527 AOT：`out_sha256` + `err_sha256` + 文本）；不变式 I1–I4 = 0 违规；前置闸 `--selfcheck` OK + 全仓 11 新文件 / 红 0；登记表 **+6 行**（258 行）`bind_evidence --check` → `R2E_R2F_EXIT=0`。
- **负控**: 前置闸注入违规文件 ⇒ 钩子判红（`GATE 12 文件 / 红 1`，`BLOCKED`）；CPM selfcheck 同包两版本必拒；源级钉死负控（只读主文件 ⇒ partial 断言红）。
- **裁决 (预注册 J1–J5)**: J2/J3/J4 **达成**；J1 **收窄**（预注册「全 src = 0」过宽：`agent.core` 下 = 0 ✅，余 31 处为**合法命名空间所有者**自身声明/引用）；**J5 未达**（`OnProcessAsync` −50 行 vs 目标 ≥300 ⇒ 只完成有界抽取，全方法语义分层结转 R528）。**本轮无 LLM 对照窗 ⇒ 不宣称任何 token/调用降幅**；`exec_precondition --round R527` **rc=3**（无题集，fail-closed），故本轮读数一律不作 R413 判据依据。
- **同轮修因**: `FrontendAskFlowTests` 隔离复现 `ClientCount` Expected 1/Actual 2 —— 与 R526 记录的偶发失败族同源（就绪探针连接的服务端注销异步收口竞态）⇒ 改**有界收敛后断言**（3s 内收敛到 1），非放宽断言。
- **下轮候选 (R528)**: ① ② 续: `OnProcessAsync` 余 1550 行按语义分层续抽（等价性夹具已就位）② 词表/豁免类判据改「所有者 vs 引用者」两段式口径（J1 教训）③ 主线对照窗重跑: 外部真值 codex 同窗 n≥3 + `exec_precondition` rc=0 才取 R413 判据读数 ④ `FrontendAskSameConnTests` 同族竞态是否同一收敛模板可修。


## R529 (2026-09-17) — 主线扩面(第二题族, 非游戏) + 外部真值失败窗 `unreliable` 判据化 + completion 按类分解天花板算式 (轮志: `docs/reports/r529-second-family-and-unreliable-policy.md`)

- **靶点**: R528 三候选同轮并推 —— ① 外部真值失败窗 `unreliable` 判据化 ② completion 2× 的下一个杠杆先做按类分解 ③ 题集扩面到非游戏族(保 58 例锚族作可比基线)。
- **夹具 (新)**: `toolkit-multimodule-v1` = 多文件工具包(工作根 `toolkit/`, `python3 -m toolkit <vm|jsonmini>`), 生成自 `eval/probe/tasks.py` seed 20260917: `vm_run` 12 例 + `json_mini` 18 例 = **30 隐藏例**(公开 4); 判分两条**非同源**实现(前置器用例脚本 / 冻结期判分器), 各自正控 30/30 + 变异体全红(26/21/0)。
- **器具 (新)**: 前置器新增**预注册驱动策略分支** —— 该窗外侧(真值)臂未全对/缺席 ⇒ 移出验收面并单列(`policy_demoted`/`unreliable_windows`), 本侧失败**一律不得被吞**; 另加 `DECLARED_ARM_ABSENT` 硬闸; 无该 key ⇒ 分支不可达(`nc_historical`: R528 rc 1→1, 验收面 diffs=[])。
- **读数 (3 窗 × 3 臂 × 2 族 = 18 格, 同窗单变量)**: 本侧 A1-on **F1 58/58 × 3 窗**、**F2 30/30 × 3 窗**; 外部真值 codex 同窗 58/58×3(F1)、30/30·30/30·**29/30**(F2, w3 漏判 `\u0007` 码点 <0x20 ⇒ 本侧判对); 消融基线 A0-off F1 58/55/58、F2 30/30×3。
- **判据列 (F2 新族, A1-on/A0-off)**: calls `0.667 / 0.714 / 4.125` 倍, new_prompt `0.416 / 0.239 / 2.387` 倍, **3 窗极差极大 ⇒ 本轮不宣称 token/调用降幅**; F1 锚族同比 calls `3.714 / 4.714 / 0.500` 倍(两窗更贵 ⇒ 门控引入额外往返, 结转 R530)。
- **completion 分解**: F2 三类 A(末端正文)/B(逐步叙述)/C(工具调用骨架) = `1040/2420/13502`(w1)、`1226/6624/140966`(w2, 含真值臂 476 次抖动)、`1209/5422/22702`(w3); 天花板乐观界 headroom 79.2%/81.8%/67.8%, 叙述占比 14.3%/4.5%/18.5% ⇒ **支配项 = C ⇒ 唯一杠杆仍是降步数/合批**。
- **裁决 (预注册 J1–J5)**: J1/J2/J4(记录列)/J5 **达成**; **J3 未达成** —— 终局 `exec_precondition --round r529` **rc=1**: 阻塞 = ① 基线臂 `w2/agentA0-off/g1 55/58`(非本侧处理臂) ② w2/w3 各臂 `UNDECLARED_SCOPE`(**预注册修正加了 w2/w3 窗却没写进 `evidence_scope.require`**, 事后禁补)。**故本轮全部降幅读数标「参考(未可验收)」, 不作 R413 依据。**
- **真实策略首用**: w3 真值臂失败 ⇒ `policy_demoted=['w3/codex']` / `removed_msgs=3` / `unreliable_windows=[w3]`, 该臂仍在全局 `blocked` 单列(不隐藏); 本侧 30/30 不受影响。负控 **6/6**(含 NC6 = 真实 w3 场景的回归陷阱: 臂键 `codex/t1` 与臂级模式 `*/codex` 恒不匹配的 bug 由此暴露并修)。
- **诚实边界**: ① 闸 rc=1 ⇒ 不宣称降幅 ② 外部真值本身不稳(F2 三窗 calls 18/476/61, w2 单臂 896.6s / 128.6k new_prompt; 含 codex 自身 `rm -f` 被拒的重试伪影) ③ 用例名 `mod#i` 的 `i` 是全局 0 基序号(报告按内容引用, 不改器具) ④ 天花板是乐观界(每步下界取观测最小值) ⑤ w2 基线臂 3 例失败未逐个定因。
- **下轮候选 (R530)**: ① **预注册 `require` 一次写全全部窗×臂**(本轮 rc=1 的唯一可控因)后重跑 ≥3 窗取 R413 判据 ② 降步数/合批(把调用数做成一等目标) ③ 定因 F1 锚族为何 A1-on 更贵(w1/w2 calls 3.7×/4.7×) ④ 真值侧伪影隔离(给 codex 夹具等价安全清理入口, 免 `rm -f` 拒绝导致抖动) ⑤ 第三题族 = 数学难题(带逐模块可测)。
