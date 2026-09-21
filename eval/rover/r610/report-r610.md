# R610 · RF0004.2 首轮 = M3 第一刀（动作候选进 R1 契约 + 本地机械裁选）

- 日期：2026-09-21（cron 60min tick）｜ 前态锚：`HEAD`（R609 之后）
- 单变量（预注册）：`AGENTFRAMEWORK_R1_ACTION_CANDIDATES`（缺省 on / 显式 `0` = 旧行为逐位）
- 状态：**机制面已落地并机检；真机臂（N8/N9）顺延** —— 顺延原因见 §5

## 1 本轮改了什么（净产品改动：6 文件 + 2 新件）

| 文件 | 改动 | 机器证据 |
|---|---|---|
| `tools/r1gen/r1prompt.py` | 新增**尾部载体块** `<action_candidates>`（追加在 `SPEC_APPENDIX` 之后、`</prefix>` 之前） | 前缀 15291→15675 字符，首次分歧在 **15283**（= 仅在 closing tag 之前插入 ⇒ 前 15283/15291 = **99.95%** 逐位不变） |
| `src/agent/contract/StructuredPrompt.cs` | 生成物（前缀 + `PrefixChars`/`PrefixSha256Pinned` 双钉子） | `gen_csharp.py --check` ⇒ `R1GEN_EXIT=0 / R1GEN_DRIFT_FILES=0` |
| `src/agent/r1/ActionCandidates.cs`（新） | 纯函数裁选器：白名单取执行面 `ActionToolDecl.Names`、必填参数由声明面 JSON Schema 派生、逐条给**可机检原因码** | 单测 6/6（正控 / 判别性负控 / 同源闸 / 零回归 / 边界 / 轴解析） |
| `src/agent/r1/R1Pipeline.cs` | 远端返回后调裁选器，落三计数（**不改变 rc/stage 任何取值**） | 定向面 80/80（含 R1 全族 + 契约面 + API 基线） |
| `src/agent/r1/R1RunResult.cs` / `R1Transcript.cs` | 三字段进台账与 `R1_STATS` 标记；**声明数 0 ⇒ 字段缺席** | 零回归机检：声明数 0 时 marker/transcript 均不含 `action_candidates` |
| `src/agent.tests/ActionCandidatesTests.cs`（新） | 六条判据（含「拒绝原因数 == 拒绝数」防空心面） | 6/6 |

**设计动因对齐**：RF0004 §1 M3「编排决策由闸族系给出，**远端只做候选声明**」；RF0004 §131 硬约束「动作候选一律走**尾部载体块**（`SupplementBlock` 形态），禁塞进前缀内部」——本轮按该约束落地（首版曾误插在 schema 段内，见 §4 自捕①）。

## 2 本轮读数（机制面）

| 面 | 判据 | 读数 | 状态 |
|---|---|---|---|
| 前缀不变量 | `gen --check` drift = 0 ∧ 双钉子单测 | `R1GEN_EXIT=0`；chars 15675 / sha `a9792fdb…` | PASS |
| 裁选器（正控） | 3 条合法候选 ⇒ declared=accepted=3, rejected=0 | 单测 | PASS |
| 裁选器（判别性负控） | 6 条含 5 类非法 ⇒ accepted=1, rejected=5，且**5 条原因码逐条可机检** | `tool_not_declared:shell_exec` / `duplicate_id:ok` / `missing_field` / `args_missing_required:write_file` / `args_not_object` | PASS |
| 同源闸 | 白名单取执行面 ∧ 契约文本枚举**逐名同序** | `ActionToolDecl.Names` 5/5 | PASS |
| 零回归（轴关） | 声明数 0 ⇒ 台账/标记**不含**三字段 | 单测 | PASS |
| 轴解析 | 缺省 on；`0`/`off`/`false` 关；`on`/垃圾值 on | 单测 | PASS |
| 形式门禁 | `VerificationForm`/`SkillGeneralization`/`DevPlanDocRef` | **14/14**（Failed 0 / Skipped 0） | PASS |
| API 基线 | 有意变更须重生 | **+16 / −0**（仅本轮新增成员：`ActionCandidates` + `R1RunResult` 三属性） | PASS（已重生） |
| 收口判据 | `status_gen.py --check` | **PASS（违规 0 / 基准漂移 0 / 缺源 0）** | PASS |
| 器具声明 | `decl_sweep.py`（只读） | `checked=30 drifted=0` | PASS |
| 真机：声明到岸率 / 裁选守恒 / 调用面 / 质量 vs codex | J1 / J2b / J3 / J4 / v3 | **未测**（真机臂顺延） | 未测 |

## 3 恒前缀基线的重钉（本轮第二产出）

`eval/capability/baselines.json` 两条冻结基准按各自 `ground_rule`（「加厚后必须重取 chars/sha 并重钉」）**已重钉**：

| id | 旧值 | 新值 | 新源 |
|---|---|---|---|
| `F_env.prefix.chars` | 15291 | **15675** | `eval/rover/r610/prefix-r610.json`（sha12 `8bfe3aa936ce`） |
| `F_env.prefix.sha256` | `f1280f71…` | **`a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e`** | 同上 |

## 4 自捕（两件，均"未放宽判据"）

**① 首版插入位置违反 RF0004 §131（已修）**：首版把 `action_candidates` 加在 `SCHEMA` 的 `refusal` 行之后 ⇒ 生成前缀首次分歧在 **1889**（*13,402/15,291 = 87.6% 的既有前缀被推移*）。修法 = `git checkout -- tools/r1gen/contract.py` 复原契约原型（生成物随之逐字节复原：`StructuredContract.cs` / `StructuredContractTests.cs` 现盘 `git diff` 为空），改以**尾部载体块**形态追加 ⇒ 分歧退回 15283。

**② 「只许加厚」基线文字与历史实践不符（新发现，如实登记）**：`F_env.prefix.chars` 的 threshold 原文写「**前 15291 字符逐位不变**」，但**该字面从来没有任何机检强制**，且历史厚化轮本身就中段插入：
`77ff7391(15119) → 56f6adee(15291)` 首次分歧在 **1641**；`55cf1f11(14863) → 77ff7391(15119)` 在 **796**。
⇒ 判「**字面不成立、实义 = 每次厚化重取 chars/sha 并重钉**」（其 `ground_rule` 已如此写）。登记件：`eval/rover/r610/prefix-r610.json:invariant_finding`；threshold 文字已同步改写。
**诚实边界**：前缀是**编译期常量**（会话内逐字节恒定 ⇒ 会话内缓存命中不受内容影响），故「中段插入 = 破缓存」**不成立**（此前首版定因把「跨轮冻结可比性」误读为「会话内命中率」）；真实的跨部署代价 = 一次冷 prefill，与历史各轮同量级（本轮 +384 字符）。

## 5 顺延（N8 发布 / N9 真机臂）——三条独立闸同时红

| 闸 | 实测 | 判据 |
|---|---|---|
| 同仓写者 | `src/agent.llamacpp/LlamaCppGeneratorOptions.cs` mtime **09:59:03**（兄弟会话 RF0006 在飞改 `src/`） | AOT 发布件无法代表「本轮 src 改动的发布件」⇒ **被测件身份不成立**；且禁拆共享编译节点（`MSBuild`/`VBCSCompiler` 在飞） |
| 内存窗口 | `MemAvailable` **1543 MB**（兄弟 `llama-server` 在跑，8B PQ2_0 RSS ≈ 2.0 GB） | 起手闸条款 `REQ = 2650 + clamp(170,60,cap) = 2820 MB` ⇒ **窗口 fail-closed** |
| 端口/命脉 | 兄弟 `agenthost --frontend-api 4399` + `timeout 260` 测量在飞 | 不得与其争端口/内存 |

**重启判据 = 只重启 N8→N9 这条边**（N1–N7 产物在盘；`prereg-r610.json` 已在臂前落盘 ⇒ 下 tick 同 prereg 起臂**不构成事后补写**）。**禁下调解闸值**。

## 6 诚实边界

- 本轮**零真机臂** ⇒ 不宣称任何质量 / 调用数 / 命中率降幅；成本三列 = **未测**。
- **M3 出口闸**（调用数按 `request_id` 去重 ≤ 旧臂 50%）本轮**不判**：远端动作只有**声明**、尚无执行接线（`git grep` 显示 `ActionCandidates.Select` 只被台账侧消费）⇒ 调用面按构造无分离（属 R611 第二刀）。
- `J4`（整题全对率）与 `v3`（对 codex 真值配对）本轮未测 ⇒ 不作能力结论。
- 铁律 11 前置器（`exec_precondition --round r610`）**本轮不适用**（零真机臂 ⇒ 无两侧落盘摘要）。
