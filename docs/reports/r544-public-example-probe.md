# R544 — `g1` 跨族长任务: **产物侧公开用例独立回放**（题面机械抽取 + 判分器同语义回放 + 管道自产证据回灌）

- 轮次: **R544**（器具目录 `eval/rover/r544/`；窗口 `w1`）
- 器具: `eval/rover/r544/{setup_r544.py, prereg-r544.json, taskset-r544.json, input-pins-r544.json, run_r544.sh, analyze_r544.py, probe_smoke_r544.sh}`
- 题面: `g1`（多模块游戏包, 58 隐藏用例, sha256 `516f3208…f3aca3`，与 R542/R540/R531/R536 **逐字节同**；装配时逐项机检 == R542）
- 二进制: `/tmp/pub_r544/agenthost`（sha256 `f516234a0acbd18e613c56a60fd8bfb0f29e5dbcdcb1317120b199b5eb2333ea`，15,812,000 B，`PUBLISH_EXIT=0`、**IL 警告 0**）—— **本轮改了产品源码 ⇒ 重发布 AOT**（发布形态铁律；命令不带 `-p:PublishAot`）
- 共 7 臂 = 开关×3 rep + 旧路径基线，**同窗** `w1`，独立 session/臂（R509 令）；同输入硬门 PASS、预注册范围闸 rc=0、起手闸 2/2 PASS

## 1. 因果链（为何是这根轴）

R542 逐臂机检给出两个事实：**① `rc=0` 的 4 个 r1 臂产物仅 43–55/58**（唯一 58/58 的 r1 臂是 `rc=5`）⇒ 「模型自述完成」不是正确性证据；**② 8/9 臂栽在 `wythoff#43–#57`，其中含 2 条题面公开用例**，而模型在计划里**自己已经跑过**该公开用例并实测到不符 ⇒ 自测闸有效但证据面是**模型自撰期望**。
⇒ 本轮唯一有证据支撑的挂点（R542 候选①）= **产物侧独立自检**：题面公开用例由**管道机械抽取**（输入/期望取自题面，禁模型自撰）、**独立回放**（与隐藏用例判分器同语义：`rc==0 ∧ stdout 尾换行归一逐字节等`）、失败则用**管道自产证据**回灌执行修复轮。

**产品面改动（单接线点，可回退）**：`AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {未设=off, 1/on/true=on}`（**默认关**）⇒
`R1Pipeline` 在 `PlanExecutor` 返回 `rc=0`（自称完成）后调用 `PublicExampleProbe`（新 5 文件：`PublicExample{,Set,Extractor,ProbeResult,Probe}.cs`），
回放不过 ⇒ `PublicProbeRepairMessage` 回灌（进入既有执行回灌预算 `MAX_EXEC_REPAIR`）；预算耗尽 ⇒ `rc=8 stage=public_probe_unmet`（成对报，`correctness_asserted=0`）。
台账新增 `public_probe_ran/total/failed`（**关闭态不出字段** ⇒ 与旧台账逐字节同）。
注：修复指令文本必须加在**生成器单一真源** `tools/r1gen/gen_csharp.py`（`src/agent/contract/StructuredPrompt.cs` 是生成物，手改会被提交闸拦下）。

**L2 证据（改链必附）**：`src/agent.tests/R1PublicProbeTests.cs` 9 例（含真题面锚：冻结 `g1` 题面抽出的 **8 条**公开用例逐条等于题面字面、分组归属 `life/sub/nim/wythoff` 各 2）；
零回归成对：同产物 + 关 ⇒ `rc=0 done`（旧行为）/ + 开 ⇒ `rc=8 public_probe_unmet`。
命令：`dotnet test src/agent.tests/agentframework.tests.csproj --filter FullyQualifiedName~R1PublicProbeTests` ⇒ **9/9**。
真机接线冒烟（`probe_smoke_r544.sh`，2 跑次）：`on ⇒ public_probe_ran=1 ∧ reply 含 R1_PUBLIC_PROBE`；`off ⇒ 字段缺席` ⇒ `PROBE_SMOKE_RC=0`。

## 2. 读数（同窗 `w1`；单变量自洽机检：`prefix_identical=True · role_mounted_all=True(326 字符) · cases_total_58_all=True`）

| 臂 | 开关 | rc | stage | 隐藏用例 | pran | ptot | pfail | 调用 | 新算 prompt | completion | 总 tok | 失败族 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `P0a` | off | 5 | expect_stdout_exhausted | **58/58** | - | - | - | 2 | 16,476 | 4,049 | 20,525 | - |
| `P0b` | off | 4 | contract | 0/58 | - | - | - | 2 | 16,240 | 3,999 | 20,239 | 全族（**契约未过 ⇒ 零执行 ⇒ 空树**） |
| `P0c` | off | 8 | self_test_unmet | 55/58 | - | - | - | 4 | 32,787 | 7,646 | 40,433 | wythoff×3 |
| `P1a` | on | 5 | expect_stdout_exhausted | **58/58** | - | - | - | 2 | 16,473 | 3,966 | 20,439 | - |
| `P1b` | on | 0 | done | **58/58** | **1** | **8** | **0** | **1** | **8,083** | **2,322** | **10,405** | - |
| `P1c` | on | 5 | expect_stdout_exhausted | 43/58 | - | - | - | 4 | 32,736 | 7,990 | 40,726 | wythoff×15 |
| `A1on` | 旧路径 | - | legacy_tool_loop | 46/58 | - | - | - | **34** | **702,146** | 12,141 | **714,287** | wythoff×12 |

- **列汇总**：`off` 全绿 **1/3**（P0a）· `on` 全绿 **2/3**（P1a/P1b）；两列 `rc=0 ∧ 非全对` 的**假成功臂数 = 0**。
- **机制启用（J1，预注册「on 臂必须 ran=1」）⇒ FAIL**：只有 `P1b` 走到探针（`ran=1 / total=8 / failed=0`，8 条公开用例**全过**且隐藏用例 58/58）。
  `P1a`/`P1c` 在 `PlanExecutor` 就 `rc=5`（**模型自撰 expect_stdout 不符**）⇒ 按设计**只在 `exec.Rc==0` 触发**，从未到达回放点。
- **代价（J4）**：on/off 中位倍率 **调用 1.0× / 新算 prompt 1.0× / completion 0.98× / 总 token 0.996×** ⇒ 本窗探针**零可测代价**（只有 1 臂真跑它，且该臂是全场最省的一臂）。
- **旧路径基线崩了（J5）**：本窗 `A1on` = **34 调用 / 714,287 tok / 46/58**；R542 **同题同窗类型**读数是 **4 调用 / 38,990 tok / 58/58** ⇒ **旧路径自身跨窗摆动 8.5× 调用 / 18.3× token**，本窗读数**不可作降幅依据**（跨窗禁相减）。
- `rc ↔ 产物正确性双向脱钩`再加一例：`P0a`/`P1a` **rc=5 而产物 58/58**（反向），与 R542 的 `rc=0 而 43–55/58`（正向）并存。

## 3. 验收（铁律 11 前置器，fail-closed）

`python3 eval/rover/r507pre/exec_precondition.py --round r544` ⇒ **rc=1**
- `blocked` 4 项（P1c 43/58 · P0b 0/58 · P0c 55/58 · A1on 46/58），其中**验收面** `blocked_scoped=1` = `w1/agentP1c-g1`（43/58）⇒ 交付面未全绿。
- ⇒ 本轮一切成本/质量推断标「**参考（未可验收）**」，**不宣称任何降幅或增益**。
- 全量回归：`dotnet test agent.sln -c Release` ⇒ **1867/1867 绿**（首跑 1866/1867：1 例 `FrontendHandshakeTests.同段多个请求_全部处理且按req_id关联` 隔离复跑 4/4 绿 ⇒ 判**同机争用假红**，非本轮回归，已如实入档）。
- 形式门禁 `VerificationForm|SkillGeneralization|DevPlanDocRef` ⇒ **14/14 绿**；**API 面重生**（`AGENTFRAMEWORK_API_BASELINE_WRITE=1`，diff = **仅本轮新增 22 行**、零删改）。

## 4. 诚实边界

1. **预注册 J1 被判 FAIL，照原样保留不翻案**（`readings-w1.json` `invariants.mechanism_on_arms_ran=False`）：探针的**触发面只有 `exec.Rc==0`**，而本窗 3 个 on 臂里 2 个在计划执行阶段就 `rc=5` ⇒ 「机制在多数臂上生效」不成立。修法方向（下轮）＝ 把回放挂到**产物已在盘的全部出口**（含 `rc=5/8`）并以其证据优先回灌 —— 这是本轮**发现**，不是本轮交付。
2. **n=3 / 单窗**：两列 `rc ∈ {5,4,8}` / `{5,0,5}`，用例 0–58 ⇒ 离散结局方差主导；R542 的「假成功臂」（rc=0 ∧ 43–55/58）在本窗**未复现**（两列 0 臂）⇒ 该现象属**窗内采样**，n=1/格不足以定性。
3. **旧路径对照列不可用（本窗）**：`A1on` 34 调用 / 714k tok / 46/58 与 R542 4 调用 / 39k / 58/58 相差两个数量级 ⇒ 该列**自身**是方差源，g1 族「r1 更省 token 且质量不降」**仍未成立/未可判**。
4. **外部真值（codex-cli）本轮未出场**：g1 的 codex 臂在 R523/R529 已判不可用（32 步上限 × 18 分钟未走完）⇒ 主线四硬条件的**外侧**缺失，本轮是内部单变量对照 + 旧路径基线。
5. **公开面 8 条 ≠ 充分**：题面公开用例仅 4 族 × 2 条 ⇒ 回放是**必要非充分**自检（`P1c` 即 8 条公开用例中 2 条不过、隐藏面再败 13 条）。禁把「公开 8 条全过」当整题正确。
6. **本轮自捕器具缺陷 1 条**（已修，记入证据）：首版回放用 shell 直跑，产物**同秒同长度**改写会让字节码 `mtime+size` 校验失效 ⇒ 旧 `pyc` 被复用 ⇒ 修复轮后仍「回放不过」（L2 单测 `Probe_Repair_Round_Reinjects_…` 首跑红即此因）。修法 = 每次回放用**独立空 `PYTHONPYCACHEPREFIX`** + `PYTHONDONTWRITEBYTECODE=1`（与判分器同语义）；修后 9/9 绿。
7. **A1on 单臂 1 次**（未超时）；`P0b` 的 0/58 是**契约未过 ⇒ 零执行**（空树按 fail-closed 记 0，不得读成「实现全错」）。
8. **API 面与回归**：新增公共类型/成员 ⇒ 基线必须显式重生（`AGENTFRAMEWORK_API_BASELINE_WRITE=1`），重生前 `PublicApiSurfaceTests` 判红（**这是设计行为**，不是回归）；重生后 diff 仅本轮 22 行。全量首跑 1 例假红（socket 握手用例同机争用）已按「隔离复跑 ⇒ 转绿 ⇒ 判假红」分诊，**不靠重跑掩盖**。
9. **生成物所有权（提交面被拦下的实况）**：`src/agent/contract/StructuredPrompt.cs` 是**生成物**（单一真源 `tools/r1gen/gen_csharp.py`）；首版直接手改该文件 ⇒ 提交时被 `R1GEN 生成物漂移闸` **拦下**（`R1GEN_DRIFT_FILES=1`）。修法 = 把 `PublicProbeRepairMessage` 加进**生成器**后 `python3 tools/r1gen/gen_csharp.py --write`（生成物与现盘差 1 字节 = 手改注释的标点/空格）⇒ `R1GEN_DRIFT_FILES=0`、**前缀钉不变**（`PrefixChars=14863` · sha `ed13dd23…`）。
10. **测量二进制与收口源的分叉（如实披露）**：7 臂读数绑定的 AOT 是 `f516234a…`（构建于**手改注释**的同语义源）；收口后按生成器单一真源重发布 = `0cff37ee…`（同 15,812,000 B、IL 警告 0）。两者源码差 = **注释 1 字节** ⇒ 二进制 sha 不逐字节可复现，本轮不重跑臂（口径：读数绑定 `f516234a`，复现性以 `0cff37ee` 为准）。

## 5. 下轮候选（R545）

① **探针触发面扩到全部「产物已在盘」的出口**（`rc=5/8`），并以**题面公开用例证据优先**回灌；预注册判据 = on 臂 `public_probe_ran=1` 比例 **3/3**（v1 的 J1 阈值不变，披露 v1 run/二进制 sha 后重跑）。
② **采样方差定量**：单剂量（开关固定）reps≥5 或固定 seed/温度后再判轴；现读数下任何单臂对照都不可信。
③ **旧路径对照列可用性定因**（R542 4 调用/58/58 ↔ 本窗 34 调用/46/58）⇒ 判该列在 g1 是否可用；不可用则主线对照面须换外部真值或缩题面规模。
④ **codex 外部列**在 g1 形态的可用性（32 步上限）—— 或用同族更小题面重挂外侧。
⑤ RF0001.3 **completion 压缩**（`KPI.md`：reasoning 吃满上限，completion 仍是最粗的一列）。
