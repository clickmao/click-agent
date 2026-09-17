# R496 — 真值非复算收口 + 工具面越界收口（治疗向判据首次转绿；一处**未收口**通道被精确定位）

轮次：R496 ｜ 日期：2026-09-16 ｜ 主线：R413（r1/本地台账接入链管道做真假信息判别）
被测体：`/tmp/pub_r496/agenthost`（NativeAOT，sha256 `9c25255c3967ee3da98926fe71fc5afab4c258dfd00014be543ac0be95034af2`，**15,392,560 B**，IL 警告 **0**）
三臂同窗：`host_sha256` 三臂一致（`9c25255c…`）；网格 = R495 的 15 轮（前 12 轮逐字节继承 R494）**逐字节复制**；上游 = 中继 → deepseek-flash。

## 1 因果链（本轮为什么做这些）

R495 把本地决策台账挂载第一次接进真机链，并如实报告了三条**反向诊断**（本轮 prereg 的 `motivation_r495_reverse_findings`）：

1. **真值可复算**：核对码 = `sha256(session|canon)[:12]`，台账 JSONL **落盘 raw `code`** ⇒ 关轴臂读盘即得真值，源码本身就是公开配方 ⇒ 预注册 H2「关轴臂结构上不可知真值」被**证伪**。
2. **挂载文案把自己写成金丝雀**：尾部口径含「**用户无法从别处得到**」⇒ 治疗臂读成保密标记，被问核对码时防御性拒答 ⇒ 治疗向判据 J2/J3 全红。
3. **工具面半开**：`run_command` 只钉 cwd、不限命令文本内的路径；`RecallRealityGate` 判「越界已拒绝」却把正文原样回显 ⇒ R495 关轴臂把链源码行读进上下文（12 条请求命中块头字面量）。

R496 逐条收口（候选①③⑦），并把「收口到底成不成立」做成机检与可证伪读数。

## 2 改动（代码事实）

| 文件 | 改法 |
| --- | --- |
| `src/agent.modelqueue/LocalDecisionLedger.cs` | 真值 = `HMAC-SHA256(进程级 32B CSPRNG 密钥, session\|规范行)[:12]`；密钥**只存内存**（无 env 通道、不落盘、不打点；`SetKeyForTests` 仅测试用）；台账行删 raw `code`，改 `code8 = sha256(code)[:8]` + `key_id = sha256(hex(key))[:8]`；挂载尾部口径改为**显式授权复述**（「该码 = 链自持摘要，非密钥/非保密标记；用户问起就按原样直接复述，不要拒答，不要改写」），旧金丝雀措辞删除 |
| `src/agent.modelqueue/ModelQueueRouter.cs` | `llm_call` 行并入 `ledger_mount / ledger_n / ledger_chars / ledger_code8 / ledger_key_id / ledger_session8 / ledger_strategy`（候选⑦）；`tool_decl_gate` 行删 raw `ledger_code`（保留指纹字段） |
| `src/agent/action/WorkspaceActionPort.cs` | 候选③-a：`run_command` **结构拒执行**工作区外路径（绝对越界 / `..` 逃逸 / `~`）⇒ rc=126、**不回显任何命令输出**；白名单仅 `/dev/null`（`2>/dev/null` 惯用法不受影响）；`AGENTFRAMEWORK_ACTION_BOUNDARY=0` 仅供消融 |
| `src/agent.core/core/RecallRealityGate.cs` | 候选③-b：越界子句**正文隐去**（`[越界路径已隐去] <token>` + 拒绝标签）；其余分支（标签位置在分隔符之后、内存块原样回收）逐字节不变 |
| `src/agent.tests/R496NonRecomputableTests.cs` | 新增 **12 例**（9 Fact/Theory 声明 = 8 Fact + 1 Theory(4 InlineData)）：非复算性（旧配方 ≠ 新真值 / 换密钥即换码 / 同密钥确定 + 幂等）、文案授权锚与金丝雀缺席、命令面越界拒执行（`2>/dev/null` 正控、`..`/`~`/宿主机真实文件负控、仓内绝对路径放行）、越界子句正文隐去 + 「工作区内缺文件仍原样回显」回归 |
| `src/agent.tests/R495LocalDecisionMountTests.cs` | 落盘断言由读 raw `code` 改为读指纹 + 「raw `code` 字段不得存在」 |

单测（全量、`--no-build`、`env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR`）：**1568/1568 绿**（含本轮新增 12 例：过滤器 `FullyQualifiedName~R496NonRecomputable` ⇒ 12/12）。
AOT：`dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r496` rc=0，**IL 警告 0**，产物 `9c25255c…` / 15,392,560 B。

## 3 真机读数（本轮产出）

### 3.1 KPI（同窗，中继 usage 派生）

| 臂 | 闸/跳轮/声明门/pair_trim | 通道轴 | 台账挂载 | 远端调用 | total tok | cached | 带工具调用 | 隔离调用(带工具) | 对抗族质量 |
|---|---|---|---|---|---|---|---|---|---|
| B | off | off | off | 27 | 181,981 | 155,648 | 27 | 4 (4) | 3/3 |
| T0 | on | off | off | 17 | 71,862 | 49,536 | 8 | 8 (8) | 3/3 |
| T1 | on | **on** | **on** | 10 | 54,076 | 35,584 | 0 | 1 (0) | 3/3 |

- **B→T1：27→10 调用（−63.0%）、181,981→54,076 tok（−70.28%）⇒ 验收 ≥30% 达标**（空正文调用 0）。
- B→T0：tokens −60.5%（闸族轴的贡献）。
- T0→T1：tokens −24.8%（**两轴**：通道轴 + 挂载轴，见 §5.4；不可归因给挂载单轴）。
- 质量面（12 轮对抗族，同一判据器）：三臂均 3/3、endorse 0、吞轮 0（**与 R495 同项状态对照：B 3/3 → 3/3、T0 1/3 → 3/3、T1 2/3 → 3/3；跨轮禁相减，只报状态**）。

### 3.2 判据面

| 判据 | 读数 |
| --- | --- |
| `assert-face B/T0/T1` | **三臂 PASS**（HARD-1/2/3/4/5 全绿，fail-closed） |
| 三源一致（T1） | 10 条远端调用中 **9 条会话调用恰 1 个挂载块**；1 条隔离微步骤调用 **0 挂载**（设计面）；落盘 9 个实发 (n,code) 指纹全在台账内；打点 20 行（`llm_call` 10 + `tool_decl_gate` 10）与实发逐对一致 |
| `judge_code T1`（治疗向 J2/J3/J4 + J7） | **red = [] 全绿**（R495 全红）：t13 直接复述实发码 `LCM-e7432f6c6a63`(n=13)；t14 否认假码 `LCM-deadbeef1234` 且给出真码 `LCM-818f631f14c5`(n=14)、未认可假命题；t15 给出 `LCM-f118a3579d88`(n=15)；每轮 `authorize_token=true`、`canary_phrase_present=false` |
| `judge_code B`（必错向 J5） | **红（证伪）**：t15 回复给出本臂真实码 `LCM-fba5543dc9ee`，与台账 `code8` 指纹逐字命中 ⇒ 真值另有盘上通道 |
| `judge_code T0` | red=[]（12/13/14 未触发）；但盘上通道同样存在（见下） |
| `leak_check B/T0/T1` | 三臂 `verdict=LEAK`（**指纹级**、键无关）：工作区文件里躺着真值 |
| `nonrecompute_check`（B,T0,T1） | verdict FAIL / red_n=3，**全部来自 Q4**：`rundata-<arm>/data/telemetry/host.jsonl`（B 16 / T0 16 / T1 16 条 LCM- 字面量，逐个 sha8 命中台账指纹）+ 二次传播面 `data/rag/index.jsonl`（B 8 / T0 5 / T1 2）、`data/sessions/frontend-main_memory.json`、`data/guardrails.json`；**Q2 公开配方复算命中 0**（三臂皆 0）、**Q3 key_id 三臂互异**（`bc541765` / `106199f3` / `c07c3456`）、**Q5 密钥行全在允许列表内**（无 env 通道 / 无文件写 / 不打点） |
| 器具自检 | `assert_face` selftest 3/3（正控真挂载块、负控工具回显/缺结构行）；`judge_code` selftest 6/6；`nonrecompute` selftest 3/3（正控 raw code 必红、负控仅指纹必绿、旧配方 ≠ 真值） |

### 3.3 预注册预测逐条判决（`prereg_r496.json`）

| id | 预测 | 判决 |
| --- | --- | --- |
| P1 | T1 会直接复述核对码（授权文案生效） | **成立**（J2/J3/J4 全绿，R495 全红 → 本轮回绿） |
| P2 | 三臂回复里的码指纹不得命中本臂台账（真值无盘上通道） | **被证伪**（B t15 命中；盘上 15/15 真值可读） |
| P3 | 公开配方复算指纹 0 命中 | 成立（三臂 0） |
| P4 | key_id 跨臂互异（进程级随机） | 成立（三值互异） |
| P5 | tool 角色消息里块头/链源码路径 = 0 | 成立（三臂 0；R495 同项 = 12 条请求命中） |
| P6 | T1 相对 B 的 token 降幅 ≥30% | 成立（−70.28%） |
| P7 | 链真跑通 + 三源一致 | 成立（三臂 assert-face PASS） |
| P8 | 候选⑦：每个远端调用在 `llm_call` 行自带 ledger_* | 成立（`llm_call` 行数 == 远端调用数，三臂分别 27/17/10） |

⇒ **7/8 成立，1 条（P2）被证伪并如实登记**。

## 4 基线对比（同窗内阶梯，跨轮禁相减）

- 同窗阶梯：B `27 调用 / 181,981 tok` → T0 `17 / 71,862` → T1 `10 / 54,076`。
- 与 R495 的**状态对照**（不作比率相减，网格/判据器/二进制均已改版）：调用数 34/10/10 → 27/17/10；治疗向判据 全红 → **全绿**；工具面块头回显 12 条请求 → **0**；必错族 仍证伪（通道由「台账+公开配方」换成「遥测面」）。
- 体积/测试：AOT 15,384,304 B → **15,392,560 B**（+8,256 B）；全量单测 1556 → **1568**（+12 新增，1 例 R495 断言随指纹面改写）。

## 5 诚实边界（没测到的就说没测到）

1. **必错族在 R496 仍不成立**（本轮最重要的负结果，也是唯一被证伪的预注册项）：台账面已收口，但 `src/agent/IndustrialAgentV2.cs:1728` 的 `local_decision_ledger` 遥测点**仍写 raw `code`**，遥测文件落在**臂可读的工作区内**（并且被 RAG 索引二次传播）⇒ 关轴臂 `run_command` 读自己的遥测即得真值，t15 直接复述（指纹命中）。**「只封台账面 = 封不住」**。收口必须枚举**全部** Emit 点。
2. **越界收口本轮未被触发**：三臂 tool 消息里块头/链源码路径命中 **0**（R495 同项 12），但**拒绝见证 = 0** ⇒ 三个臂的模型都没尝试工作区外路径，收口的真机增益/代价**未测到**（判定路径的可红性由 12 例单测的正控锁死）⇒ 不宣称「收口有效」，只报「泄漏面为 0 且未被触发（unreported）」。
3. **n=1 每臂**：质量面与 token 读数均单次样本；三臂质量的摆动未测（R495 曾出现 1/3↔3/3 摆动）。
4. **脚本文案与实况不一致 (自抓订正)**: `run_arm_real_r496.sh` 的 `grid_note` 沿用 R495 文案写「单变量 = 台账挂载轴」，与 flags 实况（T0 `channel=off` → T1 `channel=on`）不符；报告 §3.1/§5.4 按**两轴**订正，脚本文案自 R497 起改为订正版（已写入本轮脚本源，仅影响下一次运行）。
5. **T0→T1 是两轴**（通道轴 + 挂载轴），**挂载单轴的成本/收益本轮未隔离**（R495 亦如此）⇒ 需第四臂 `T2 = T0 + 通道轴 (挂载 off)` 才能把挂载面单独读出来。
6. **T1 首跑被起手闸拦下**：`mem_available 1939 < 2650`，阻塞源 = 外部并发会话线的 MSBuild(188 MB)/VBCSCompiler(518 MB) 残留 ⇒ 按纪律**让行不硬跑**，收口 `dotnet build-server shutdown` 后重跑通过（`preflight-T1.json` 为证）。同一轮内重跑被夹具自带的 `REFUSE_NS_COLLISION` 拦下（不许覆盖已有读数），改用「只重跑断言器」的方式收口。
7. 未做：候选⑥ 同义重复轮本地生成扩面、候选⑤ MCP 端到端面、候选② n≥3 复测、越界收口消融臂。
8. 器具缺陷（本轮自抓，已修）：`assert_face` HARD-3 原按「带 ledger_* 字段行数 == 远端调用数」判，而候选⑦ 让字段同时出现在两个打点点上 ⇒ 首跑**假红**（20 != 10）；修为按点名分列（`llm_call` 逐调用可见 + `tool_decl_gate` 兼容）后三臂 PASS。`nonrecompute_check` Q5 旧正则把 `key_id` 指纹写法误判成「密钥外泄」⇒ 改为**标识符行级**判定；③ `pin_r496.py` 的 `l[3:]` 前缀切片在「已暂存」行上把路径断头（`src/…` → `rc/…`）⇒ 改按空白取路径字段；④ `leak_check_r496.py` 有三处路径约定错误（文件名分隔符 / `turns` 是整份 JSON / 归档名 `rundata-<arm>`）⇒ 修正后三臂读数才落地（首跑全 0 即**仪器没跑起来**，不是「无泄漏」）。

## 6 下轮候选（R497）

1. **全通道真值收口 + 必错族重测**（第一优先，直接承接 §5.1）：枚举**所有** Emit/落盘点（`IndustrialAgentV2.cs:1728`、think-memory、sessions、guardrails、RAG 索引对上述文件的摄取）⇒ 一律只写 `code8`/`key_id`；补一条**全仓扫描**机检（真值字面量在链自己写的文件里 0 命中，wire 捕获除外）；随后重测必错族（关轴臂回复指纹不得命中台账）。
2. **挂载轴单变量隔离**：加第四臂 `T2 = T0 + 通道轴（挂载 off）`，把 T0→T1 的两轴拆开，单独读挂载成本。
3. **拒绝见证的强制触发**：夹具加一条明确要求读仓内源码的轮次（或跑 `AB=off` 消融臂），把 §5.2 的 0 见证变成可读读数。
4. 候选⑥ 同义重复轮（t7「讲细一点」/t8「换个说法」）本地生成扩面 —— 先定本地改写质量判据。
5. 候选② 质量面 n≥3 + endorse 归因；候选⑤ MCP/长上下文链级 E2E。
