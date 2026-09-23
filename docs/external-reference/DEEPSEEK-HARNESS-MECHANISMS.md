# 外部参照面 · DeepSeek Harness（deepseek-ai/deepseek-harness，dsh）的机制采编

- 日期：2026-09-24 ｜ 采集人：R642 会话（WHY）
- 仓库：`github.com/deepseek-ai/deepseek-harness`（MIT，TypeScript monorepo，发布 2026-08-13，developer preview，兼容性破坏警告在位）
- 性质：**只读源码参照（RF0001 采编面）**。未 clone 全库、未编译其 TS、未跑其测试 ⇒ **全部为机制假设**，不可当实测结论引用（承 ZCode 采编口径）。
- 取件方式：GitHub API `git/trees/master?recursive=0`（15,180 条目）+ raw 逐件；聚焦 `packages/compaction/*` 与 `packages/guard/*`、`packages/core/session/src/invariant.ts`，共 **31 件**于 `/tmp/dsf/`（含 zh 变体剔除、tests 剔除）。取件脚本 `/tmp/dsh_fetch.py`、扫描 `/tmp/dsh_scan.py`。

## 为什么看它

它与本仓同题面（agent harness、远端 LLM、工具环、缓存敏感），且是 DeepSeek 官方基准方法学里点名的 minimal 模式载体。与 ZCode（上下文装配/治理闸）互补：**dsh 的强项 = 压缩事务化 + 事件日志不变式 + 循环卫生**。

## 采集事实 | 值

| 事实 | 值 |
|---|---|
| 根树条目 | 15,180（blob+tree） |
| `.agents/notes/` 架构决策笔记 | 数百篇，按 `architecture/bug-fix/feature/simplification` 分目录、带日期与 zh 双语 —— **决策留痕文化与本仓 EVIDENCE/registry 同构** |
| compaction 包结构 | `compaction`（契约层）/ `compaction-basic`（缺省实现）/ `command-compact`（手动 /compact）/ `compaction-image-offload` / `compaction-tool-result-pruner` |
| 压缩触发 | `pressure`（阈值 `floor(min(W×0.8, W−O−headroom))`，headroom 缺省 65,536 tok）与 `context-overflow`（provider 确认溢出后强制减）双触发 |
| 压缩事务 | `compaction/start → summary → end` 括号 + `compactionId` 唯一标识 + **锁**（start 即锁，end 解锁）；失败走 `compaction/summary-error` waterfall 可恢复 |
| 切割边界 | `toolPairingBalancedBefore/After(session, seq)`：切点必须落在 **tool-call/result 配对平衡**处，WeakMap 缓存增量折叠 |
| 摘要复用缓存 | 摘要请求**重放 system prompt 与最后 routed request 的前缀** ⇒ 摘要调用本身吃 warm prefix（不付全价） |
| tool-result-pruner | 超 8,192 code points ⇒ 头 4,096 + 尾 1,024 + marker；Unicode 码点切（不劈 surrogate pair）；**零模型调用**；原事件留在 append-only 日志，替换件以 `sourceEventSeqs` 引用 ⇒ **回放安全** |
| shadow price | `compaction/prune` 事件记录被替换区间的精确 token 计价（log-only），tokenMeter 是唯一计价权威 |
| 事件日志不变式 | `invariant.ts` 独立 companion：校验 `compaction/start→summary→end` 括号配对、**owner-turn 包络**（括号不得跨 turn 边界）、checkpoint `compactionId` 与 start 匹配；孤儿 start 由 `session/end-seed` 边界判 stale |
| session 不变式 | `request/header` 等事件的关系不变式独立成包（`dsh-invariants` 服务注入） |
| 循环卫生（guard） | `repeat-tool-reminder`：同 tool 同参数连续重复达 thresholds [3,5,8] ⇒ 注入提醒（首档短句/后档带 500 字符参数预览）；**零阈值前 token**、append-only 不破缓存、fail-loud 配置校验、内存态不落日志 |
| timeout-policy | 独立 guard 包，工具超时策略与循环解耦 |
| 遥测 | OTel 双包（product/session），default-off，匿名 user-id |

## 对本仓的帮助面（逐条带对照证据）

### 有帮助（候选采纳面）

**D1 · 压缩事务三件套**（bracket + lock + invariant）——本仓 `src/agent/context/` 1,010 行里 `SessionInjectionPlanner` 只有插入账本（InjectionLedger），**没有压缩**。若未来做上下文压缩，直接采这套形态：① 压缩 = 日志事件（不是原地改写）；② 切点必须 tool-pairing 平衡（我仓的 `SupplementBlock`/`ArtifactCarryover` 同样有「切在工具对中间」的隐患面）；③ 不变式独立成机检件（可挂进 roundcheck 家族）。

**D2 · tool-result-pruner 形态**——大回执头/尾保留 + marker、原事件留档 + seq 引用、零模型调用。我仓现状：`IndustrialAgentV2.cs:234` 回执 digest 截 400 字符、`ContextAssembler.Prompt.cs:60` 每条 200 tokens 硬截，都是**无引用留档的破坏性截断**。采纳其「留档 + 引用 + 可回放」三保证可把截断从信息丢失降级为**可回读的投影**——直接呼应 R584 文件插件三硬保证（备份/竞争/合并）的回执版。且「Replay-safe replacement + shadow price」与 KPI 口径令（计价 unreported 禁 0）同构。

**D3 · 摘要复用 warm prefix**——摘要请求重放既有前缀。本仓铁律 12 恒定前缀只许加厚 + 精排 KPI 令「不破坏缓存」⇒ 若做压缩/摘要，**摘要调用本身也必须吃 warm prefix**，这是现成形态答案（`PromptCacheChannelTests` 前缀冻结 sha 可直接复用为判据）。

**D4 · repeat-tool-reminder（循环卫生）**——我仓 `ActionLoopRunner.cs`（245 行，`DefaultMaxSteps=6`）只有**步数顶棚**，grep 无「同参重复调用」检测；R1 修复循环（`_R1_MAX_EXEC_REPAIR`）同理。阈值 3/5/8 渐进提醒 + 参数预览截断 + append-only 不破缓存，机械可采（纯增量打点 + 提醒注入，零决策变更），可作 R6xx 零产品改动候选或放行后接进 ActionLoop。

### 不采纳 / 暂缓

| dsh 机制 | 裁定 | 理由 |
|---|---|---|
| Cordis「一切皆插件」内核 | 不采纳 | 本仓 AOT/零反射红线 ⇒ 运行期插件装载与 NativeAOT 冲突（反射装载禁用）；且 50 万行 TS 的插件面不在本仓工程预算内 |
| 四预设运行模式 | 暂缓 | 本仓形态是「NLP 决策主体 + 本地只打分」，无多模式需求；若未来出 benchmark minimal 档可回看 |
| OTel 遥测 | 暂缓 | 本仓遥测已有 host.jsonl + 中继 dump 双口径；OTel 引入属新依赖，与预算锁冲突 |
| e2b/landlock 沙箱 | 不采纳（本轮） | 本仓零 shell 纪律 + 单机 2 vCPU，沙箱面暂无threat model |

## 与 ZCode 采编的合并视图（三轮外部参照现状）

| 机制域 | ZCode | dsh | 本仓现状 | 优先级 |
|---|---|---|---|---|
| 前缀安全落点 | C1 段声明契约（cacheHint/injectionTarget） | 摘要重放 warm prefix | 前缀 sha 冻结已有，**段声明面 0** | C1 仍排首位 |
| 压缩 | compact policy/microcompact（未深采） | **事务化 + 不变式 + pruner**（已深采） | 无压缩 | D1/D2/D3 入队 |
| 循环卫生 | runtime-command-queue 背压 | repeat-tool-reminder | 只有 MaxSteps=6 | D4 候选 |
| 治理闸 | 基线+过期+抑制计数（**已采纳 R616**） | — | 已落地 | 关闭 |
| 决策留痕 | .architecture-baseline | .agents/notes 决策笔记族 | EVIDENCE + registry | 同构，无动作 |

## 注意事项（诚实边界）

1. **未 clone / 未编译 / 未跑其测试** ⇒ 全部为机制假设；深采面只有 compaction + guard 两族，`agent-loop`/`skill`/`subagent` 等未读。
2. raw 直连可用（本轮实测 200/14,149 B），未走 gh-proxy；API 树一次 15,180 条目全量到手。
3. 首轮 fetch 因前台 300s 超时 + 后台进程工作目录漂移两次失败，最终串行 + 断点续跑拉齐 31 件 —— 取件数以 `ls /tmp/dsf | wc -l` = **31** 为准。
4. 本文件只写机制，不写本仓改造结论；改造须另立轮次循 `external-reference-adoption` 纪律（零 `src/` / 预注册 / 单变量）。
