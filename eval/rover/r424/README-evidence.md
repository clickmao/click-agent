# R424 证据台账 — 主线 KPI 在 **AOT 发布形态** 上的复现（R413 形态口径缺陷修复）

- 轮次: **R424**（R423 由并发对端流占用 = 检索 tf 饱和；命名空间碰撞两侧均登记，见 §7）
- 计划（判据预注册正文）: `docs/plans/v0.45.0-r424-aot-mainline-replication.md`（§3–§5 落盘 17:05:36，**先于**首臂读数 17:06:23）
- 器具: 本目录 `run_arm.sh` / `prov_check.py`（形态闸）/ `verdict_r424.py`（结算器）/ `drive_task.py` / `stub_openai.py` / `task.json`
- 判定: **PASS**（9 预注册判据 + 5 事后检查全绿；`verdict-r424.json`）
- 产品代码改动: **零**（本轮只补测量器具与形态闸）⇒ 无需 AOT 重发布；被测 AOT 产物 = 工作树 HEAD 的发布产物

## §1 因果链（为什么起这一轮）

1. R413 台账（`eval/capability/kpi.jsonl` round=R413）登记 `agenthost_bytes: 15138848 / aot_il_warnings: 0` ⇒ 宣称读数为 AOT。
2. 但其臂执行器 `eval/rover/r413/run_arm.sh:12` 的被测路径是 `src/agent.host/bin/Release/net10.0/agenthost`。
3. 该路径实测 = **78,256 B** 的 .NET **apphost 壳**（同目录并存 `agenthost.dll` 179,712 B）；
   `env -i <bin> --version` ⇒ `You must install .NET to run this application.`（rc=131）⇒ **需要运行时 = IL/JIT**。
4. 时序：臂 A `calls-A.jsonl` mtime 10:57、臂 B 12:04:44；`publish_aot.sh -o /tmp/pub_r413` 产物 mtime **12:07:16** ⇒ **AOT 建在测量之后**；
   且全仓无 `publish → bin/Release/net10.0/` 拷贝脚本（该路径唯一写入者 = `dotnet build`）。
5. ⇒ R413 的 `12/16,888 → 8/7,007` **只是 JIT 中间证据**，其 `agenthost_bytes` 属事后另做的 AOT 构建，**不是被测对象的身份**。
   （诚实措辞：不断言「一定不是 AOT」，断言「形态未验证」。）
6. 本轮动作：在**可自证的 AOT 产物**上重测同一判据，并把「形态自证 + 成对负控」做成硬闸。

## §2 被测产物身份（V0 形态闸）

| 项 | 读数 |
|---|---|
| 被测二进制 | `/tmp/pub_r423/agenthost`（路径名与对端流发布目录同名，非本轮号） |
| 字节 / sha256 | **15,168,064 B** / `2d363b6d132b06e23a0f994fc91d9de6ab41737d42a3ee3c6e77eb50d2edc15b` |
| IL/trim 警告 | **0** |
| 自证（`env -i <bin> --version`） | 打印 `AgentFramework CLI` ⇒ **原生**（无需运行时） |
| 成对负控（同命令 / IL apphost） | `rc=131 You must install .NET…` ⇒ 闸有判别力 |
| 归档副本 | `/tmp/pub_r424/agenthost`，sha256 **逐位相同**（防同名目录被后续发布覆盖） |

与 HEAD 的差异面：并发对端流当时有未提交改动，但 `git diff --name-only -- src/agent/IndustrialAgentV2.cs src/agent.modelqueue src/agent.host` 为**空**
⇒ **门/账本模块未被改**，读数不受对端检索改动污染（该改动随后由对端自行提交）。

## §3 三臂读数（外部真值：桩侧逐请求落盘 + 驱动器观测 + 遥测）

条件：同桩（`stub_openai.py`）、同任务脚本（与 R413 **逐字相同**：8 轮 = 4 实质 + 4 寒暄）、同 `role=skeptic`、同 config 模板；仅 local 段开关不同。

| 臂 | local 段 | 远端调用 | 远端 token(估) | 被跳过轮 | 机制 |
|---|---|---|---|---|---|
| **A** | 无 | **12** | **16,888** | — | 基线（分母） |
| **B** | 有（模型在，`turn_gate:true`） | **8** | **7,007** | 2/4/6/8 | 4 次真 r1 判别消化非实质轮 |
| **B′** | 有（`model_path` 指向不存在文件） | **12** | **16,891** | 0 | 门开但设备缺 ⇒ 4 次 `decided=false` 降级远端 |

- **C1 远端调用 ↓ = 33.3%**（12→8）≥30% ✅
- **C2 远端 token ↓ = 58.5%**（16,888→7,007）≥30% ✅
- **C5 B′ ≡ A**（调用 12==12；token 差 0.018% ≤5%；跳过 0；无崩溃/hang）✅
- **C6 r1 归因**：省下 4 调用 == 4 个非实质轮；**B′ 无 r1 ⇒ 增益归零** ⇒ 增益不是机械门的功劳（机械门自身零节省）✅

与 R413 对照：臂 A `12 / 16,888`、臂 B `8 / 7,007` **逐位相同** ⇒ ① 该任务上 JIT 与 AOT 读数**不可分**；② R413 证据的**本体**成立，本轮补的是**身份**。

## §4 门真身（V1）与 role 额外数据挂载（用户令「记得要挂载 role 的额外数据」）

- V1：臂 B 遥测 `local_turn_gate_config = {turn_gate_enabled: True, local_channel_ready: True, role: 'skeptic'}`；
  门事件 **7** 条 = 3 条 `mechanical:pass→local`（轮 1/3/5，0 远端 0 r1）+ 4 条 `gate:skip→local`（轮 2/4/6/8，真走 r1，raw 长度 144/331/521/128）。
- **role 数据真挂载（源码 + 实证两源）**：
  - 调用点 `src/agent/IndustrialAgentV2.cs:1481`：`JudgeTurnAsync(message.Content, ActiveRole.Id + "|" + Clip(ActiveRole.ProfileSeed, 80), null, ct)`；
  - `TurnGateJudge.BuildPrompt`（`src/agent.modelqueue/LocalGenerationPort.cs:234`）把 roleSeed 作为 `【角色设定】` 插入本地门提示（成长经历块有界 ≤300）；
  - **实证 ProfileSeed 非空**：桩侧捕获的远端系统提示内含 `【角色:疑问者】你是一个低调但执着的追问者…`（同 run 同字段）⇒ 门提示的 role 片段非空（成长经历形参 `null` = **未挂**，登记为边界）。
- **P4**：4/4 Skip 事件的 r1 原始输出内含**当轮用户原文** ⇒ r1 读到的确是用户消息（非空壳调用）。
- **P3 失败可见性真机成立**：4/4 降级事件带 `decided=false` + `error=local_failed:LlamaCppException` + `basis=gate:degraded:failed_or_empty→remote`。

## §5 质量面（C4/P1）

- 每轮 `ok=true` 且回复非空（三臂一致）；
- 被跳过轮回复 = 21 字**非 LLM 模板** `收到，继续按当前方向推进，本轮不重新规划。`（不新增内容，不幻觉）；
- **P1**：非跳过轮（1/3/5/7）回复与臂 A **逐字节相同** ⇒ 实质轮无质量回归；
- 诚实边界：「质量不降」= 上述两条 + 零假阴性，**未做**人类/LLM 质量评分。

## §6 仪器纪律（本轮新增/沿用）

- 形态闸（V0）落在器具里，**跑测前 fail-closed**：判不过就不许出读数。
- 计数口径：外部真值（桩侧逐请求），非被测量代码自报计数器；token = `chars/2` 估算（两臂同口径 ⇒ 比值有效）。
- 判据预注册 + **事后判据单列**（`checks_posthoc`，`posthoc_participates_in_verdict: false`）——避免事后判据回填主判据。
- 归属：驱动器落 `t_start/t_end` 绝对时间戳、桩落 `ts` ⇒ 逐轮归属可算；已知残余 = 轮边界异步判官调用有 ±1 轮滑移（总量精确、未归属 0）。
- 沿用：`background=true` 长跑；固定端口；三臂串行；跑完即清进程。

## §7 命名空间碰撞（一等事件，两侧均登记）

- 本轮启动时与**另一并发执行体**撞在同一轮号：对侧 = R423「跨会话检索打分 tf 饱和」（`eval/capability/r423/`，含计划 `v0.44.0-r423-tf-saturation.md`）。
- 两侧产物路径不重叠（`eval/rover/*` vs `eval/capability/*`），但共享轮号与 `v0.44.0` 前缀。
- 处置：**本侧让号至 R424**（17:10:36 迁移 `eval/rover/r423/ → eval/rover/r424/`，计划改名为 `v0.45.0-r424-…`）；
  R423 归对侧（检索打分）；**未改写历史、未删对侧产物、不只静默改名**（对侧台账 `namespace_collision` 字段已登记对侧视角）。
- 根因：取 max+1 前未复跑完整「活动执行体（pgrep）+ 锁 + 目标轮文件 mtime」占用序列 ⇒ 下轮起把该序列作为启动硬闸。

## §8 复现命令

```bash
cd /home/agentuser/AgentFramework
bash eval/rover/r424/run_arm.sh A   47830 47840 "$PWD/skeptic.rbin"   # 分母（无 local 段）
bash eval/rover/r424/run_arm.sh B   47830 47841 "$PWD/skeptic.rbin"   # 治疗（r1 门）
bash eval/rover/r424/run_arm.sh BP  47830 47842 "$PWD/skeptic.rbin"   # 无设备负控 / r1 归因
python3 eval/rover/r424/verdict_r424.py                                # 结算 → verdict-r424.json
```

回归抽查（本轮零产品改动，故为抽查非背书）：`env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release --filter "FullyQualifiedName~TurnGate"` ⇒ **47/47 通过**。

## §9 诚实边界（汇总）

1. 增益**归因 r1**（B′ 归零）；**不**归因机械门。
2. 降幅**依赖非实质轮占比**：本任务 4/8=50% ⇒ −33.3% 调用/−58.5% token；占比 0 ⇒ 降幅 0（1/8 ⇒ 仅 −8.3%）
   ⇒ 用户令「一轮任务总 token ↓≥30%」在**该任务形态**达标，**不外推**为任意形态保证。
3. token 为 `chars/2` 估算，非真 tokenizer。
4. 「质量不降」未做人/LLM 评分；跳过轮为许可模板（非生成内容）。
5. 逐轮归属对异步判官调用有 ±1 轮滑移（总量精确）。
6. 轮 7 三臂一致走「等你回答」本地澄清分支（0 远端调用，回复 168 字）⇒ 非远端实质轮，同形 ⇒ 不污染差分。
7. 门提示内容**不可直接观测**（只能由源码 + ProfileSeed 实证推断）⇒ 下轮加打点。
8. n = 1 脚本 × 3 臂，单机单批，非分布；未测并发会话下的门行为。
9. R413 台账的 `agenthost_bytes=15138848` 与本次被测产物**不是同一字节**（15,168,064 B / `2d363b6d…`）⇒ 两轮读数可比（逐位相同）但产物不同源。
