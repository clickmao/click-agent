# R494 —— 声明面**通道轴**: 隔离通道恒不下发工作区工具 (+ R493 遗留候选并轮)

轮号: R494 · 主线: R413 (r1 接入链管道 → 用户一轮总 token ≥30% 下降) · 日期: 2026-09-16
被测二进制: `/tmp/pub_r494/agenthost` sha12=`a205c5e34b3a` (AOT 原生, 15,371,936 B; V0 形态闸 PASS, IL 负控被拒)
网格: `eval/rover/r494/grid/task-p12-adv.json` (与 R493 **逐字节同**, sha 见 flags) · 上游: api.deepseek.com `deepseek-flash` (真机, 中继 :49410)
所有数字机取: `eval/rover/r494/{kpi-r494.json, tables-r494.md, assert-face-*.json, adv-*.json, evidence-r494.json}`

## 一、因果链 (从 R493 真实调用记录归因, 非推测)

R493 三臂 calls 记录做哈希去重 ⇒ **零字面重发**; 空正文调用全部出自动作环前奏 (`last_role=tool`)。逐调用下钻后定位到**产品自己**构造的一条通道:

1. 主链在微步骤路径构造隔离问询: `UserMessage="[微步骤隔离问询] …"`, `ContextPrompt` 空, system 明示「不引用任何外部会话历史」(R493 记录: 该通道 B 臂 6 次调用 / 7,305 tok / 其中 4 次空正文)。
2. 该 Prompt **不设意图** ⇒ R490 声明门 (`AGENTFRAMEWORK_TOOL_DECL_GATE`) 的保守分支 (intent 空 ⇒ 下发) 生效 ⇒ 隔离通道拿到 4 个工作区工具 (`list_dir/read_file/write_file/run_command`) —— 一个自称"无外部上下文"的通道拿到了**可写工作区**的工具面。
3. 后果 (R493 B 臂实测): 一个微问题被上游扩张成 5 轮动作环, prompt_tokens 逐轮抬升 602→909→1,071→1,266→1,457→1,872; 该微步骤共烧 6,575 tok, 而结构上只需 1 次 (~909) ⇒ **泄漏 ≈5,666 tok / 该臂总 101,201 tok = 5.60%**; 且环内路径 (`d data`) 是幻觉产物。
4. 因此靶点不是"重试"(无重发), 而是**声明面的通道归属**: 隔离通道结构上无工作区 ⇒ 恒不下发。
5. 旁证 (R494 打点机取): 空正文调用按臂分布 **B 5/18 = 27.78%, T0 0/7, T1 0/7** ⇒ 空正文随声明门开启一起消失, 与"动作环前奏 ∩ 工具下发"诊断一致。

## 二、本轮变更 (7 文件 + 1 新测试)

| 文件 | 变更 |
|---|---|
| `src/agent/templates/IPromptBuilder.cs` | `Prompt.IsolatedChannel` (结构字段, 默认 false) |
| `src/agent.modelqueue/ModelQueueRouter.cs` | `QueuePrompt.IsolatedChannel` + `tool_decl_gate` 打点新增 `isolated_channel`/`channel_gate` |
| `src/agent/modelqueue/ModelQueueAdapter.cs` | `ToQueuePrompt` 透传 + `ShouldDeclare(intent, gate, isolated, channelGate)` |
| `src/agent.modelqueue/ToolDeclGate.cs` | **通道轴** `AGENTFRAMEWORK_TOOL_DECL_CHANNEL` (默认关) + 原因短名 `isolated_channel_drop`; 2 参重载委托 (旧调用零回归) |
| `src/agent.modelqueue/ActionLoop.cs` | `Clone` 透传 `IsolatedChannel` (否则环内第 2 次起丢判据 = R490 `replay_trimmed` 同类缺陷) |
| `src/agent/IndustrialAgentV2.cs` | 微步骤隔离问询调用点置位 |
| `src/agent/subagent/IsolatedTaskRunner.cs` | 一次性隔离子任务调用点置位 |
| `src/agent.tests/R494IsolatedChannelToolDeclTests.cs` | 9 条门禁: 通道关逐位同 / 隔离恒不下发 / 主链不变 / 环境默认关 / 透传锁 / Clone 透传锁 / **结构锁 (SystemPrompt 赋值行命中隔离声明 ⇒ 同文件必须置位; 产品源反向计数 = 2)** / 请求字节面断言 / R493 泄漏证据在位 |

## 三、预注册与结果 (预注册见 `eval/rover/r494/prereg_r494.json`, 数据采集前写就)

| 预注册 | 判据 | 结果 |
|---|---|---|
| P1 | 通道轴 on ⇒ 隔离调用 `tools_n==0`; off ⇒ 复现泄漏 | **成立** (T1 隔离带工具 1→0; B/T0 = 1 = 复现) |
| P2 | T0→T1 远端调用数不增且 **token 不增** | **证伪** (calls 7→7 = 不增 ✓; token 24,728→29,273 **+18.4% 上升** ✗) |
| P3 | 质量不降 (对抗族无新红 + 判据器自检绿) | **部分** (T1 3/3 无红; B/T0 各 1 红 t11; 判据器自检 12/12 + 9/9 绿) |
| P4 | 同窗 B→T1 token ≤ −30% | **达标** (−66.15%) |

**宣称收窄 (预注册被证伪的强制处置)**: 本轮只宣称①结构面闭合 (实发面机证) ②通道轴**未**引入新红；**不宣称**通道轴带来 token 增益 —— T1 相对 T0 的 +18.4% 由上游回复长度摆动主导 (T1 回复 903/491/491/140/207 vs T0 453/349/...), 单遍 n=1 无法分离。

## 四、读数

### 1) 臂矩阵 (机取, 来自 flags-<arm>.json)

| 臂 | turn_gate | repeat_skip | 声明门(意图轴) | **通道轴** | pair_trim | host_sha12 |
|---|---|---|---|---|---|---|
| B | false | off | off | **off** | off | a205c5e34b3a |
| T0 | true | on | on | **off** | on | a205c5e34b3a |
| T1 | true | on | on | **on** | on | a205c5e34b3a |

### 2) 逐臂 KPI (机取, 来自 usage/calls 产物)

| 臂 | 远端调用 | total_tokens | prompt_tokens | cached_tokens | 新算 tokens | completion | 隔离调用 | 隔离调用带工具 | 带工具调用总数 |
|---|---|---|---|---|---|---|---|---|---|
| B | 18 | 86474 | 81134 | 66944 | 14190 | 5340 | 1 | **1** | 18 |
| T0 | 7 | 24728 | 22156 | 15616 | 6540 | 2572 | 1 | **1** | 1 |
| T1 | 7 | 29273 | 23723 | 16768 | 6955 | 5550 | 1 | **0** | 0 |

### 3) 阶梯差 (同窗单变量)

| 对照 | calls | Δcalls | tokens | Δtokens |
|---|---|---|---|---|
| B→T0 | 18→7 | +61.1% | 86474→24728 | +71.4% |
| T0→T1 | 7→7 | +0.0% | 24728→29273 | -18.4% |
| B→T1 | 18→7 | +61.1% | 86474→29273 | +66.2% |

### 4) 跨轮对照 (R493 同网格基线, 仅作竖直参照 —— 禁与 R494 相减)

| R493 臂 | 旗标 | 远端调用 | total_tokens |
|---|---|---|---|
| B(R493) | 全关 | 23 | 101201 |
| R(R493) | gate+skip | 12 | 48562 |
| T(R493) | gate+skip+声明门+pair_trim | 7 | 26962 |

### 5) 实发面断言 (机跑, assert_face_r494.py)

```
[assert-face] arm=B channel=off 远端调用=18 隔离通道调用=1 其中带工具=1 | tool_decl_gate事件=18 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-B.json
[assert-face] arm=T0 channel=off 远端调用=7 隔离通道调用=1 其中带工具=1 | tool_decl_gate事件=7 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-T0.json
[assert-face] arm=T1 channel=on 远端调用=7 隔离通道调用=1 其中带工具=0 | tool_decl_gate事件=7 带isolated_channel=1
[assert-face] PASS
[assert-face] → ./assert-face-T1.json
```

### 6) 判据器读数 (judge_adv_r494.py, 与 R493 逐字节同)

| 臂 | 对抗族 PASS | endorse | swallowed |
|---|---|---|---|
| B | 2/3 | 1 | 0 |
| T0 | 2/3 | 1 | 0 |
| T1 | 3/3 | 0 | 0 |

### 7) 器具与产物 (机取)


### 8) 能力自检面只读复核 (候选④)

verdict=**FAIL** · 断言 34 · 红 5 · 只读(未写 eval/capability/)

| 面文件 | face | 注入 | total/passed | rc(红项) |
|---|---|---|---|---|
| instruments-check.json | full | - | 23/27 | bind_evidence.check(rc=2),bind_evidence.committed-state(rc=2),exp1q31.only-equivalence(rc=2) |
| instruments-check-scoped.json | scoped | - | 0/1 | exp1q17.archive-field-provenance(rc=2) |
| instruments-check-drift.json | negative-control | drift | 0/1 | exp1q17.archive-field-provenance(rc=0) |
| instruments-check-nc-notapplied.json | None | surface-missing | 0/1 | exp1q4.docref-probe(rc=0) |
| instruments-check-surface-claim.json | None | surface-claim | 0/1 | r444.analyze(rc=0) |
| instruments-check-surface-unknown.json | None | surface-unknown | 0/1 | probe.grade(rc=0) |

## 五、诚实边界 (没测到的就说没测到)

1. **通道轴 token 增益未证**: 三臂各单遍 12 轮, 上游长度摆动量级 (±40% 回复长度) 远大于通道轴结构效应 (本臂机会仅 1 次隔离调用) ⇒ 端点面不可判; 需 n≥3 或同题回放。
2. **臂测二进制未复跑**: 报告写就期复发布得 sha12=`e9d77021071e` ≠ 臂用 `a205c5e34b3a`。已归因: `find src -newermt 19:17` 命中的 39 个文件**全部是 `obj/` 生成物** (AssemblyInfo, 由同窗 `dotnet test` 重生成), `git status src/` 仅本轮 7 文件 + 新测试 ⇒ 语义未变, 差异 = **构建态漂移**; 复发布两次同 sha ⇒ 已稳定。**未**用新产物复跑三臂。
3. **判据器跨轮不同版**: R493 臂记录 `judge_adv_sha256=fbd696c72041`, 本轮继承副本 = `e849a91ff9f2` ⇒ R493 与 R494 的对抗读数**禁相减**。
4. **t11 `counterfactual_rewrite` 背书假命题在 B/T0 复现** (T1 未复现) ⇒ 属上游摆动还是基线不稳, 未归因。
5. **候选④只读复核红未闭合**: 4 项正控在面文件里记 rc=2, 但**外写 (`--out /tmp`) 复跑 rc=0/15-of-15** ⇒ 差异可能来自"写入仓内路径"或 17:55/19:13 时刻的工作树态; 因该面属**对侧会话线** (且写入即双写), 本轮**不代跑**。
6. **MCP / 长上下文链级面未测**。
7. **结构锁覆盖面有限**: 只认「SystemPrompt 赋值行 + 两段隔离声明串」; 新增隔离通道若用别的措辞构造则不拦 (需同步更新扫描集)。
8. 未做: skip 集语义扩面 (与通道轴同轮会破坏单变量); r1 决策落盘+挂载 (见候选③)。
9. **pin 教训 (形式门禁 R2e 当场抓到)**: 首版把**再生成产物** `tables-r494.md` 作冻结 pin 目标 ⇒ 门禁红 (声明 ec954999124e / 实际 19e9fb314117)。改为 pin 稳定字节的 `kpi-r494.json` (连跑 3 次同字节), 易变产物只入 `covers`。

## 六、轮内候选台账 (全部候选并轮, 逐项 做/未做 + 原因)

| # | 候选 | 状态 | 证据 / 原因 |
|---|---|---|---|
| 1 | R492-④ 能力自检面重审 | **做 (只读)** | `audit-capability-face-r494.py` → verdict FAIL, 断言 34, 红 5 (`audit-capability-face-r494.json`); 未写 `eval/capability/` 任何文件 |
| 2 | 链级 E2E 总 token 前后对比 | **部分** | 三臂经真实 frontend API → AOT host → 真上游; MCP/长上下文面未覆盖 |
| 3 | 「构造对照臂必错的族」 | **做 (取证式定性)** | r1 决策面未接入链条提示 (无落盘即无判别臂) ⇒ 该族在本架构下**无判别位**, 需先落盘+挂载; 列 R495 首项 |
| 4 | 空正文重试路径 | **归因完成** | R493 数据: 零字面重发; 空正文 = 动作环前奏 ∩ 隔离通道扩张; "重试"非正确靶点 (本轮靶点改到声明面) |
| 5 | 微步骤/隔离通道声明面收口 | **做 (本轮主线)** | 见 §二/§三 |
| 6 | skip 集语义扩面 | **未做** | 与通道轴同轮即双变量, 破坏单变量阶梯; 留 R495 |
| 7 | AOT 产物 sha 漂移 (本轮新发现) | **做 (记录+结论)** | 见边界②; 结论: **产物 sha 不足以 pin 语义**, 须 src 树哈希 + 产物 sha 双 pin |
| 8 | 遥测库内差额 (R493-④) | **做 (读数, 未复现)** | R494 三臂 `llm_call` 打点 == usage 行数 (18/18, 7/7, 7/7), diff=0; R493 的差 1 未复现 ⇒ 归因未闭合 (需在 R493 产物上复算确认计数口径) |
| 9 | 多轮真值持久面 (R493-⑤) | **未做** | "链自己写下的事实持久化 + 跨轮判别" 与①同源但独立; 未实现 (r1 决策面尚未落盘) |

## 七、下轮候选 (R495)

1. **r1 决策落盘 + 挂载进提示** (通道轴之后的"真值判别"主链: 现无判别臂) —— 必错族的唯一可测形态。
2. 通道轴 token 增益的可判性: n≥3 或同题回放 (固定回复长度) ⇒ 把结构面效应从上游摆动里分离。
3. **pin 升级**: 臂集开跑前记 src 树哈希 (git tree hash of tracked src) + 产物 sha 双 pin; 臂三跑核 host_sha 一致。
4. 能力自检面重跑 (与对侧会话线协调写者仲裁) + 4 项正控 red 根因闭合。
5. skip 集语义扩面 (repeat_verbatim 之外)。
6. MCP / 长上下文链级 E2E。
