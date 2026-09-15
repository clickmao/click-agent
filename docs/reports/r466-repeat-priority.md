# R466 —— 复述回放 vs 承接反问的优先级 (修 R465 预注册判据 C3 FAIL)

上游 R465 (a9158bf)。预注册 `docs/plans/v0.83.1-r466-repeat-priority.md` (跑前落盘)。二进制 `/tmp/pub_r466/agenthost` (AOT 0 IL, 15,335,040 B)。

## 因果链
R465 C3 FAIL 的机制: `再讲一遍。`(t6) 是纯复述轮 ⇒ skip 层已按 `repeat_verbatim` 回放上一条答复 (21 字), 但 R458 承接反问**收口面无条件覆盖** ⇒ 用户看到 46 字「我这边没有待办指令 (本会话还没有产物)。继续什么？」—— 复述轮被判成本会话空产物。根因 = 结算类只在打点处算一次, 收口面不知道本轮已本地确定性结算, 于是拿**空事实集**重算接地性并覆盖。

## 改动 (三处, 单源)
- `ContinuationBrief.SettleRepeatVerbatim = "repeat_verbatim"` (口径唯一字面值) + `ShouldApplyFallback(settleKind, reply, facts) = !Settled(settleKind) && NeedsFallback(...)`; 常量漂移会让规则静默失效 ⇒ 机检锁死。
- `IndustrialAgentV2`: skip 支把结算类写进**单一变量** `_localSettleKind = replyKind` (打点与收口面读同一处); 逐轮清零 (粘滞会让下一轮承接反问被误抑制); 收口面改为 `applyFallback = ShouldApplyFallback(...)`。
- 开关 `AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY` 默认 on (生产行为); 置 0 = R465 行为 ⇒ 同二进制单变量负控 (判据必须绑机制)。
- 测试: `ContinuationBriefTests.R466_RepeatReplay_...` (含 3 组负控) + `LocalTurnGateTests.G40` (结构门) + G37 强化 (主链禁字面值)。

## 同网格 4 臂 (p12 / 同桩 / 同 role / 同一 AOT 二进制)
| 臂 | 设定 | 调用 | 远端 tok | t6 可见答复 | 判决面 |
|---|---|---|---|---|---|
| Arole | 门关 | 13 | 32,097 | 46 字承接反问 | 0 事件 |
| **R** | 优先级 on | **6** | **14,529** | **21 字 = 上一条答复逐字** | 12/12 ok, repeat 2, local 4 |
| NC | 优先级 off (同二进制) | 6 | 14,531 | 46 字 (复现 R465) | 12/12 ok, repeat 2 |
| R2 | 优先级 on 复跑 | 6 | 14,531 | 21 字 | 逐位同 R |

## 预注册判据 (跑前落盘, 全绿)
- C1 降幅 ≥30%: **54.73%** (14,529 vs Arole 32,097; 调用 6 vs 13) ✓
- C2 质量 (修 R465 C3): 12/12 ok; t6 = 上一条答复**逐字** (21 字, R465 为 46 字被覆盖); t9 = 15 字逐字 ✓
- C3 零回归: 非复述 10 位的 (basis, verdict) 序列与 R465-R 逐位相同; skip kind 序列 = [template×4, repeat_verbatim×2] 同 R465 ✓
- C4 负控 (同二进制/同网格/单变量): NC 复现 46 字缺陷, 且 calls 与 R 相等 (6=6) ⇒ 开关只动覆盖面 ✓
- C5 零假跳: prefilter_violations = 0, repeat = 2 ✓
- C6 复跑逐位: R ≡ R2 (调用/token/判决/逐轮答复全同), Δtok = +2 = `run-R`→`run-R2` +1 char × 2 次调用 (R465 已立之归因律) ✓
- posthoc: Δtok(本版 R vs R465-R) = **+0** (14,529 = 14,529); 机制层遥测单源可证: R 收口 {suppressed:true, settle_kind:'repeat_verbatim', priority:'on'} vs NC {apply_fallback:true, settle_kind:'', priority:'off'} —— 两臂 skip 事件逐位同 (msg_sha16 一致, 21 字回放) ⇒ 差异只在收口优先级。

## 基线对比
- 远端调用数: Arole 13 → R **6** (-53.8%); 远端 token: 32,097 → **14,529** (**-54.73%**, ≥30% 达标)。跨轮稳定: R465-R / R465-R2 / R466-R / R466-NC / R466-R2 五次独立跑全部 6 调用 / 14,529±2 tok。
- 全量单测: 1411/1411 绿 (基线 1409 + 本轮新增 2)。AOT: 0 IL 警告, 15,335,040 B (与 R465 同尺寸, sha 9f5f9e69… vs e895ae3d…)。

## 诚实边界
- **Arole 分母跨轮漂移未消除**: R465-Arole 21 调用/33,323 tok vs R466-Arole 13/32,097。已定位 = 判官路由 (遥测 `judge.source`): R465 8 次 judge 走**远端**(本地通道未就绪, prompt_len 282–297 / tok 148–155), R466 8 次同 prompt 走**本地**(eval 222–237, 0 远端 token) ⇒ 分母含本地就绪度变量。两种分母下结论均成立 (56.40% / 54.73%), 但「Arole 作为稳定分母」这一前提本轮被证伪 ⇒ 下轮须固化分母 (判官强制本地 + 预热门)。
- t7 的 49 字前缀在 R/N C/NC 均不变 (来自用户提问追踪, 非本轮改动面); 未做真实流量复验 (本轮只有 p12 网格); 未测 AOT 运行期内存。
- R465 的 C6 FAIL (Δ+2) 在 R466 被同网格复现并归因, 但**未**改判为 PASS (口径单列)。

## 下轮候选 (R467)
① 分母固化: 判官强制本地 + 就绪门 (消除 Arole 13↔21 漂移); ② 真实流量 (state.db 1542 轮) 复验 −54.7% 的外部效度; ③ 门控轮稳态延迟 (17.6 tok/s 下界, 参数瘦身); ④ 真实计费口径 (k=1.221 + cache 命中) 纳入结算; ⑤ 嵌入通道告警真实命中取证。
