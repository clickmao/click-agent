# R576 · RF0002 §2 形状通道**接线轮**（远端回执 → 学形状 → 生产判定面消费 → 评分回执）

> 口径来源（用户令 2026-09-19 13:42 逐字）：「不补回，加入远端返回后可以优化 nlp 能力的机制，直接开始真正的主线」；
> 及同日前序逐字：「llm 返回新数据只要有一个评分机制，下次使用时有用就留、没用就扔掉」「这不是你需要开发的东西，比如那些器具」。
> 载体 `docs/plans/RF0002-nlp-self-improvement.md`（前台会话 13:49 落盘 §1 机制）。
> 排除项遵守：**不新增器具 / 不新增判官 / 不新增夹具 / 零新增开关**，只扩 `agent.nlp` 一个模块 + 现有调用点接线。

## 0. 起手核验（先判「写了没有」再判「生效没有」）

| 核验 | 方法 | 读数 |
|---|---|---|
| `LearnFromRemote` / `ReportOutcome` 有没有**生产消费者** | `grep NlpGate.(Observe\|LearnFromRemote\|ReportOutcome)` 全仓 | 改前**零消费者**（仅测试）⇒ §1 是**孤岛**（纯函数测绿 ≠ 接线通） |
| 写入点现状 | `TurnGateJudge.LearnOnSuccess` | 仍走 `NlpGate.Observe`（**逐字补丁**）⇒ 与用户令「不补回」相反 |
| 并轮前置 | `pgrep dotnet` / 在飞写者 | 无在飞构建；同仓存在前台会话未提交产物（归属见 §5） |

## 1. 修改点（4 文件 · 2 通道 · 1 评分面）

| # | 文件 | 改动 | 语义 |
|---|---|---|---|
| A | `src/agent.modelqueue/TurnGateJudge.cs` | `LearnOnSuccess`: `Observe` → `LearnFromRemote(..., localizable: true)` | **写入通道**由逐字字符串换成形状（用户令「不补回」） |
| B | `src/agent.modelqueue/TurnGateJudge.cs` | `IsPureRepeat(m, patches)` = 结构面 ∧ (`IsPatched` ∨ `IsLearned`) | **消费通道**：形状命中可在生产判定面成立 |
| C | `src/agent.modelqueue/LocalParaphraseChannel.cs` | `IsPureParaphrase(m, patches)` 同上（面 = `para`） | 改写族同形；⑤ 族互斥保持 |
| D | `src/agent.nlp/NlpGate.cs` | `IsLearned(text, face, libraryMode)` 新重载：`libraryMode=false` ⇒ 恒 false | **纯函数口径**：注入补丁模式不读进程级形状库 ⇒ 机检/差分用例**顺序无关**（R575 双侧断言的「无补丁」基线不被污染） |
| E | `src/agent/IndustrialAgentV2.cs` | 4 处评分回执：本地消化成立 ⇒ `useful: true`；3 个降级点（`repeat_no_replayable_prev` / `paraphrase_no_replayable_prev` / `paraphrase_guard_rejected`）⇒ `useful: false` | 用户令「有用就留、没用就扔掉」的落地点 = **真实结局**，不是预测 |
| F | `src/agent.tests/NlpGateLearnTests.cs` | +5 接线断言（含 3 负控） | 断言面从 `NlpGate` 内部**上移到产品判定面** ⇒ 孤岛不可再通过 |

**通道相容性**：补丁面**只读不写**（历史库与 R575 的 11 条双侧断言保持原样），形状面为**新增并入** ⇒ 本面行为是旧面的超集，`patches != null` 的注入路径逐位不变。

## 2. 真机读数（编译/测试）

| 面 | 命令 | 读数 |
|---|---|---|
| 定向（判定面 + 端口差分 + 形状） | `dotnet test --filter "NlpGateLearnTests\|LocalTurnGateTests\|R498LocalParaphrase\|R497Fingerprint\|GateRulesPortDiff"` | **Failed 0 / Passed 158 / Skipped 0** |
| 形式校验（当轮） | `env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test --filter "VerificationForm\|SkillGeneralization\|DevPlanDocRef"` | **Failed 0 / Passed 14**，rc=0 |
| committed-state 独立物化 | `git worktree add --detach <tmp> HEAD` ⇒ 在**检出树**内 `dotnet build` 两工程 + `dotnet test` 定向过滤 | **agent.nlp 0 error / 测试工程 0 error**；定向 **Failed 0 / Passed 158**（rc=0）⇒ 「提交即可自足编译」得证。**该步是本轮第二个自捕**：先前的 `git status --porcelain src/` 复核发现 `src/agent.nlp/LearnedShape.cs`（§1 前台会话新建）**未跟踪**，若按首次提交收口，检出树会缺类型 ⇒ 提交不可编译（工作区绿只是因为该文件在本地）——已 `git add` 后 amend |
| 全量套件 | `dotnet test src/agent.tests/agentframework.tests.csproj` | 首跑 **Failed 2 / Passed 1908**（FULL_RC=1）；2 例红 = `PublicApiSurfaceTests` 的**全部两条**（`I_公共API面与基线逐行相等` / `NC_比较器非恒绿`）⇒ 根因 = **新增公共成员未重生 API 基线**（设计行为，非回归）⇒ `AGENTFRAMEWORK_API_BASELINE_WRITE=1` 重生：`docs/api-surface.baseline.txt` **+12 / −0**（12 行全为 `agent.nlp` 新增成员，无整表重排／无归属篡改）⇒ 复跑 **Failed 0 / Passed 1910 / Total 1910**，FULL2_RC=0 |

## 3. 接线自证（本轮唯一承重判据）

- **正控**：`LearnOnSuccess("再讲一遍。", true)` ⇒ 学形状 ⇒ `TurnGateJudge.IsPureRepeat("再说一遍。")` = **true**
  （同面**不同措辞**被生产判定面吸收 ⇒ 学到的是能力，不是字符串）。
- **负控三项**：① 不学 ⇒ false；② 注入补丁模式（`patches` 非空）⇒ false（纯函数口径）；③ 跨面（改写形状不得被复述面吸收）⇒ false。
- **远端失败不学**：`success: false` ⇒ false。

## 4. 诚实边界

1. **生产库为空**：`data/nlp/` 目录不存在 ⇒ 形状库/Patch 库均无数据 ⇒ **真机链路当前零命中**（结构面已通、效果面**未测到**）；「未测到」不得读成「无效」。
2. **真机远端调用为 0** ⇒ **不宣称任何 token / 调用降幅**（§3 判据只证接线，不证收益）。
3. 形状泛化的**误命中率**在真实分布上未测；结构护栏（复述/改写白名单字符集）仍是硬线 ⇒ 含内容字/问号/数字的长句永不进本地面。
4. `ReportOutcome` 的**淘汰曲线**（有用加分上限 +4 / 一次无用即剔除）在真实分布上未观测。
4c. **铁律 11（可验收前置）当前呈断链**：`eval/rover/r571/verdict-r571.json` 的 `iron11` 字段指向 `eval/rover/r507pre/precondition-r571.json` —— 该文件**不存在**（该目录最新一件为 `precondition-r570.json`）；且 R571 的判决本身为 `rc=1 judge=mechanism-not-engaged`（A1 行使面未过 ⇒ 质量/成本对比作废）。最近一件真实前置 `precondition-r570.json` 读数 `executable_and_correct=False / acceptable_scoped=False`、`blocked` 非空（集中 `wythoff` 族，如 w144/R570E2 47/58）⇒ **主线判据（可验收的同窗对照）尚未达成**，任何降幅读数只能标「参考（未可验收）」。
4b. **API 基线重生是设计行为**：新增公共成员 ⇒ `PublicApiSurfaceTests` 必红（本轮首跑 2 例红即此因）；重生差异 **+12/−0** 已逐行核对为 `agent.nlp` 新增面（含 §1 前台会话的 `LearnedShape`/`ShapeCounters`/`LearnFromRemote`/`ReportOutcome` 与 §2 的 `IsLearned(...,bool)`），**不得把此类红读成回归**。
5. 本轮的 `IsLearned` 库模式开关把「注入模式」定义为**不读库**；生产（`patches == null`）才读库 ⇒ 两态分离，但两态**未做跨进程持久化真机验证**（`gate-shapes.txt` 装载路径由单测覆盖）。

### 4d · committed-state 机检抓出的**既有**结构性缺口（非本轮引入）

- 读数: 在 `git worktree add --detach HEAD` 的**干净检出树**里跑 `VerificationFormTests.Registry_Exists_And_HasNoViolations` ⇒ **1 例红**，报 **22 项违规**，形态全为 `covers 登记的路径不存在` / `evidence_path 不存在` / `evidence_cmd 引用不存在的路径`，指向 `data/probe/**`、`eval/rover/**` 产物（权威清单全文落 `R576-committed-state-registry-vf.txt`）。
- 机理: 这些产物**未跟踪**（本机在场 ⇒ 主树判定绿）⇒ 登记表的证据面**不可从提交复现**。
- 定级: **既有缺陷**（本轮未改登记表；`git ls-files` 缺档可证）；同属「判据只在主树成立」的假绿形态。
- 处置: 本轮**不修**（属「证据是否随提交」的裁定 + 用户令「不许新增夹具和额外开发」）⇒ 落 R577 候选。
## 5. 归属与自捕

- **归属**：`src/agent.nlp/{NlpGate.cs,LearnedShape.cs}`、`src/agent.tests/NlpGateLearnTests.cs` §1 五条、`docs/plans/RF0002-*.md` §1 由**前台会话**（qqbot，13:42–13:49）实施；本 tick 实施 §2 接线（A–F）并**代为落盘提交**（该批产物此前未提交，避免唯一副本长期悬空）。提交信息与本文均显式区分两侧产出。
- **自捕（1 处，起手即拦住）**：`LearnFromRemote` 有测试、有实现、**零生产消费者** —— 若只按「§1 已 5/5 绿」收口，本轮会把**孤岛**记成「机制生效」（本仓反复踩过的形态：纯函数测绿 ≠ 接线通 / 覆盖器恒 0）。
- **代际保护**：新增的 5 条接线断言写进既有测试类（同类的形状库隔离），避免新建并行测试类与既有静态 `PatchPath` 竞争。

## 6. 下轮候选 (R577)

① **形状通道真机首验**：走一次真机链路（本地端口 + 远端轮）使 `ShapeCounters.ShapeLearned/ShapeHits > 0`，把 §4-1 的「零命中」变成 **≥1 事件**（含命中面不增加远端调用数的成对断言）。
② **评分淘汰曲线观测**（真实分布上的形状存量变化；零开发，只读取数）。
③ R571-② 契约修复预算轴第二窗集（≥25 跑次/臂）或按天花板冻结 + 写死重开条件。
④ R572-③ 起手闸把会话工具子进程并入判据（**器具改 ⇒ 须先落预注册**）。
⑤ R572-① g1/`wythoff` 失分面修复 与 R572-④ 交付闸语义（`rc=5`/`rc=8`）仍**待放行**。
⑥ **补跑 R571 的可验收前置**（`python3 eval/rover/r507pre/exec_precondition.py --round r571`）并把断链指针修实——铁律 11 的收口件缺失会让上一对照轮的降幅永久停在「参考（未可验收）」。
⑦ **裁定「登记表证据是否随提交」**（4d）：随提交归档 / 显式声明不随提交 / 改 `cmd_expect_absent` 三选一，并给「干净检出树跑登记表机检」配成对控制（主树绿 ∧ 检出树红=现状）。
