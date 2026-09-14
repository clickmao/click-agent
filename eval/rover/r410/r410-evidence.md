# R410 证据 —— 会话长前缀复用（K2b 落点）/ 宿主生命周期缺口

状态: 已实施（R410，2026-09-14）
计划文档: `docs/plans/v0.32.0-r410-session-prefix-reuse.md`

## 判据（开跑前预注册）

- **J1** 会话形态（长前缀 + user）第 2 次同前缀请求：`cache_n / prompt_n ≥ 0.97`
- **J2** 短独立 prompt（R409 权威 96B 形状）：绝对 `cache_n << 4224` ⇒ 结构上不达标
- **J3** 负控（前缀首 token 改变）：`cache_n` 必须归零
- **J4** `cache_prompt=false`：`cache_n` 必须恒为 0

读数来源：llama-server `/completion` 的 `timings.cache_n` / `timings.prompt_n`（**服务端自报**，非估算，非墙钟推算）。

## A. 探针（同一 server / 同一 slot，单线程 `-t 1`，f32 KV，flash-attn off）

| 臂 | prompt_n | cache_n | 复用比 | 墙钟 |
|---|---|---|---|---|
| session_cold（P1 首次） | 4255 | 0 | — | 233.9 s |
| **session_warm_same_prefix**（P2 同前缀） | **5** | **4250** | **0.9988** | **0.5 s** |
| session_cache_off（P2，`cache_prompt=false`） | 4255 | **0** | 0 | 176.6 s |
| negative_prefix_first_token_changed（P3） | 4256 | **0** | 0 | 162.6 s |
| short_cold（R409 权威 96B 串） | 18 | 0 | — | 1.0 s |
| short_warm（同一短串重复） | 1 | **17** | 0.94 | 0.1 s |

判定：`J1=true, J2=true, J3=true, J4=true`；短形态对 4224 红线的覆盖 = **0.402%**。

**两条关键结论**
1. 机制成立且极陡：长前缀第二次请求只重算 5 token（墙钟 233.9 s → 0.5 s）。
2. **比值不是 KPI，绝对长度才是**：短形态「复用比」0.94 看着不低，但可复用前缀只有 **17 token** ⇒ 对 K2b 红线（≥4224）覆盖 0.402% ⇒ 结构上不可能达标。若只看比值会得出相反结论。

原始文件：`prefix-reuse.json`（分臂增量落盘）、`prefix-reuse.log`、`prefix_reuse_probe.py`。

## B. 产品通路（E2E CLI）+ 宿主生命周期缺口

| 运行 | PromptMode | ReuseMode | promptTokens | CachedTokens | SessionReuseCalls | SessionCacheMisses |
|---|---|---|---|---|---|---|
| run1 | chat_template | Session | 487 | **0** | 1 | **1** |
| run2 | chat_template | Session | 487 | **0** | 1 | **1** |

⇒ 即便 `--reuse on`（cache_prompt=true）+ 稳定 487 token 前缀，**跨进程复用恒为 0**：每次 CLI 调用新起一个 llama-server（新 KV 缓存）。
新增的 `SessionCacheMisses` 把这类静默失效显性化（无需人查）。

接线事实（grep 取证）：嵌入通路 `src/agent/extensions/ServiceCollectionExtensions.cs:244` 已是 `AddSingleton<ITextEmbedder>`（长驻）；
**生成本地通路目前只有 E2E CLI 调用点**（`agent.host/LlamaCppCommand.cs`），产品侧无长驻接线。

⇒ **K2b 达标三条件（缺一不可）**：① 长驻 server 进程；② 稳定长前缀 ≥4224 token；③ `cache_prompt=true`。
本轮实测：缺 ① 时 ②③ 都白搭（复用 0%）。

## C. 测试

- 新增 `CompletionReuseTests` **4/4**（口径映射负控：Session⇒`CachePrompt=true`；Reconciliation⇒`false`；greedy 采样器链；非 greedy 保留全链）。
- R409 闸门测试 `LlamaCppPromptGateTests` **9/9** 仍绿。
- 全量：**1076 / 0 失败 / 0 跳过**（R409 基线 1072 + 新增 4）。

## D. 本轮顺带修掉的两个真缺陷（均由全量回归暴露，非本轮改动引入）

1. `SessionPerformanceTests.GetRecentMessages_BeatsFullTableSort_AtScale`：以**墙钟比值（3x 阈值）作判据**，CPU 争用下翻转假红（并发时失败 / 串行复跑通过），且不绑定组件行为 ⇒ 改为「等价性作判据、计时只作信息」（R402 纪律），测试名改为 `..._MatchesFullTableSort_AtScale`。
2. `LlmServiceStatusTests.Query_Online_FieldsSane`：固定 5 s 就绪截止 ⇒ 负载下假红（全量并发失败 / 单独复跑 4/4 通过）⇒ 判定为**存活上界**而非性能判据，放宽到 30 s 并把实测等待写进失败信息（暴露就绪延迟分布）。

两者同属一类：**用不可复现的量（墙钟）当闸门**。本轮不改产品行为，只改判定器。

## E. 诚实边界

1. 探针是「同一 server、同一 slot、**顺序**两请求」；**多会话并发争用**（多 slot 抢缓存）是另一 regime，本轮未测。
2. 长前缀形态只有 **1 例**（4249/4255 token）；未做前缀长度扫描（多长才「够」的分布未测，只钉了 1 个刚过红线的点）。
3. 生命周期演示用的是 487 token 前缀（成本考虑），不是红线长度；它证明的是「跨进程复用 = 0」这一性质，不是长度性质。
4. 「长驻」是必要条件不是充分条件：还需**前缀稳定**。本轮未测「前缀中段变化会砍掉多少可复用 token」（截断点分布）。
5. 墙钟读数受同机争用影响（cold 233.9 s vs cache_off 176.6 s 的差异来自并发构建/测试，不是机理差异）⇒ 本轮**不把墙钟作判据**，判据只用 `cache_n` 计数器。
6. 产品侧长驻接线**未做**（本轮只做口径、记账、入口与可见化）⇒ R411 候选。
7. 台账缺口：R402–R407 仍未回填 `docs/improvements.md`。
