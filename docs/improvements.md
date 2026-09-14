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

---

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
**台账缺口（遗留）**：R402–R407 未回填本台账，其证据在 `eval/rover/r40x/` 与 `docs/plans/v0.2x-r40x-*.md`。

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
- **exp8 立项**（用户本轮新钦定）：[已验证产物 → skill 蒸馏 + skill 生命周期 + KPI A/B](docs/plans/v0.22.0-exp8-artifact-to-skill-and-kpi-ab.md)（设计文档，含 tokens/轮数/asked 率/质量 对照口径与 A1–A6 机检草案）。
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
- **L1 验证形式入规范 (用户长期焦点, 本轮交付)**: 新增 [docs/验证形式规范.md](docs/验证形式规范.md) (证据阶梯 L0 未验证 → L1 静态 → L2 单测/组件行为 → L3 真机运行 → L4 对抗负向控制; 六条规则: 无登记=未验证 / 静态最高只能报 L1 / L≥2 必须负向控制 / 证据必须落盘可复查 / 表述纪律 / 登记表机检) + [docs/verification-registry.json](docs/verification-registry.json) (机读登记表, 含 `covers[]` 覆盖插件实现) + `src/agent.tests/VerificationFormTests.cs` **6/6 通过** —— 含**自检负向控制**: 注入 5 类缺陷 (缺负向控制/静态冒充运行/证据路径不存在/插件漏登记/等级越级) 全部被抓出。已挂 README + 总纲 §0-0 第 9 条。
- **L2 自上下文能力差异 + 首批修复**: 新增 [docs/plans/v0.22.0-l2-capability-diff.md](docs/plans/v0.22.0-l2-capability-diff.md) (16 项逐条对位, 判定只用 `file:line` 实证; 缺口清单 G1–G9 入长期看板)。
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
- **探索产出 (5 路并行只读侦察 + 真机实验 + 本机基准, 未改业务代码)**: [docs/plans/v0.22.0-exploration-index.md](docs/plans/v0.22.0-exploration-index.md) + exp1…exp5 五份独立文档 (含现状事实带行号 / 候选方案对比 / 推荐 / 关键约束 / 验收标准 / 排除项 / 待确认)。
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
