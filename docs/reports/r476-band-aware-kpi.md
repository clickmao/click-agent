# R476 · 红线判定分档化（分档上限 + 达成轮占比 + 分通道）

状态: 已收口｜commit：本地（未 push）｜前轮：R475（`3d49bef`）

## 1. 为什么改（R469/R470 两条已收口结论的必然结果）

- `命中率 = 1 − 新/前缀`，其中**用户轮长度不可压** ⇒ 对长用户轮，结构上限 `prefix/(prefix+用户轮+21)` 本身就低于 0.97。
- R469 实测：400 条真实轮里 **50.5% 落在上限 < 0.97 的档**（94–200 / 201+ 两档）⇒ 单值 97% 口径对它们是**结构性不可达**，继续按单值判只会长期「不达标」，无法区分「结构不可达」与「机制退化」。
- 因此判据是 `目标 = min(0.97, 该轮结构上限)`：短档仍按用户钦定 0.97；长档按该档理论上限，缺口只在**上限之内**才判红。

## 2. 改了什么（产品，只增不改）

| 面 | 改动 | 事实位置 |
|---|---|---|
| 判定器 | `TurnOverheadTokens=21` / `TurnBands{0-30,31-93,94-200,201+}` / `BandOf` / `CeilingFor` / `CeilingFromGrowth` / `TargetFor` / `ToleranceFor(64/cacheable)` / `PrefixTokensNeededForBand` / `BandVerdict` 5 态 / `BandFields`(7 字段) / `BandLine` | `src/agent.modelqueue/PromptCacheRedline.cs` |
| 打点 | 三处 `llm_call` 同源铺：`cache_band` / `cache_band_source` / `cache_ceiling` / `cache_band_target` / `cache_margin` / `cache_growth` / `cache_band_verdict` | `src/agent.modelqueue/ModelQueueRouter.cs` |
| KPI 脚本 | 分档聚合（达成轮占比 + 分通道 + unknown_band）+ **常数源码 fail-closed 机检**（py ↔ C# 逐值，差异非空 ⇒ 退出码非 0） | `scripts/kpi_cache_hit.py` |
| 计价面④ | 无价格表 ⇒ `pricing.status=unreported`、`cost_cny=None`；伪造 0 被 `pricing_violations()` 判红 | `eval/rover/r475/join_usage_truth.py` |
| 器具⑤ | `bind_evidence.py --round`（默认 = 旧常量 ⇒ 无参调用逐字不变） | `eval/capability/bind_evidence.py` |

判决 5 态：`not_applicable`（轮<2 或无前缀）/ `unreported`（率=−1，**不入分子分母**）/ `at_target`（率 ≥ 目标 − 容差）/ `below_ceiling`（**上限内有空间 ⇒ 判红**）/ `below_target`（短档未达红线 ⇒ 判红）。

## 3. 判据与结果（器具 `eval/rover/r476/band_verdict_r476.py`，15/15 全绿）

| 判据 | 内容 | 结果 |
|---|---|---|
| C1 | py 侧红线/承接开销/缓存单元/档界 ↔ 源码逐值机检 | 差异 **0** |
| C2 | r469 夹具 12 组上限 + 4 组「达 97% 所需前缀」逐值复算 | **全等**（1e-4 / 0.05） |
| C3 | r469 json ↔ py ↔ 产品单测字面量三方一致（含红线） | **一致** |
| C4 | 口径**非换皮**：长档 rate 0.923446 < 单值红线 0.97，且 ≥ 上限 0.9386−容差 ⇒ 单值判越线 ∧ 分档判 `at_target` | **分歧成立** |
| C5 | 真实遥测 43 调用：判定轮 **0**、`unreported` 0、`not_applicable` 43 | **禁宣称达标**（诚实读数） |
| C6 | 负控 NC1–NC5（below_ceiling / below_target / unreported 不入判定 / 两向非恒绿 / 判红同向） | **5/5** |
| C7 | 计价面 fail-closed（无表 ⇒ unreported 且 cost=None；伪 0 ⇒ violations 非空）+ selftest | **绿** |
| C8 | `bind_evidence.py --round`（--help 可见 / 默认常量保留 / global 声明在首次使用前） | **绿**（本轮曾抓到 SyntaxError ⇒ --help 非 0 即判红） |

产品单测：`PromptCacheBandTests` 20 例 + `PromptCache*` 共 **50/50**；接线锁测试同步加强（三处打点必须同时铺分档 7 字段，`cache_ceiling` 禁硬编码 0）。

## 4. 输出效果（对比数据）

- **判据面**：97% 单值红线对 400 条真实轮的 **50.5%** 结构性不可达（R469 读数）⇒ 旧口径下这些轮**永远**记「不达标」；新口径下它们的目标 = 各自上限，缺口只在上限之内才判红 ⇒ 可区分「机制退化」与「结构不可达」。
- **真实遥测（43 调用 / 29 会话）**：分档判定轮 **0**，`not_applicable` 43 ⇒ 达成轮占比在真实面上**仍无样本**（同会话多轮真实样本 = 0，承 R470）。
- 不变式：红线 **0.97 数值未动**；`cache_ceiling` 未知一律 **−1**（禁 0 冒充）。

## 5. 验证

- AOT：`/tmp/pub_r476/agenthost` **15,355,520 B**、sha16 **`db187e0eae7f26ea`**、IL **0**、`publish_rc=0`、`env -i --version` **rc=0**、`ldd` 无 `libcoreclr`。
- 全量单测 ×3（**1451 例** = R475 的 1431 + 本轮 20）：run1 **1450/1451**（1 例闪失败）、run2 **1451/1451**、run3 **1451/1451**；闪失败 = `FrontendAccessControlTests.令牌桶_突发耗尽后拒绝_随时间恢复`（**时间敏感**、与改链面无交集）⇒ 隔离复跑 **×5 全绿** ⇒ 判负载/时序 flake，非回归（证据 `eval/rover/r476/isolated-flake-r476.log`）。
- 台账：registry **135 → 139** 行（4 行 R476，均 L2 + negative_control + 纯路径 covers）、taskplan **44 → 45** 节点、`kpi.jsonl` **74 → 75** 行。

## 6. 诚实边界

1. 真实面**判定轮 0** ⇒ 分档达成率的真机证据仍未取到（离线夹具 + 单测为唯一证据）。
2. 真实调用的档由 `growth`（≥ 用户轮）**上偏代理**派生（`band_source=growth_upper_bound`）⇒ 档位偏大；用户轮 token 未进遥测。
3. 计价面价格表未取到 ⇒ 「命中 ⇒ 省钱」仍是未验证前提。
4. 本轮零真实调用、未起 llama-server（`MemAvailable` 1984 MB < 2650 MB 起手闸）。
5. 分档只改**判决口径**，未改任何压缩/前缀机制 ⇒ 不改变 token 绝对值。
6. 全量 ×3 未能三次全零（run1 单例时间敏感闪失败，隔离 ×5 全绿）⇒ 与 R475 同类处置：以隔离复跑证伪回归。
7. 文档冲突仍在：`docs/improvements.md` 最新节停在 v0.81.0·R462、`iteration-master-plan.md:384` 仍写 `rows=102/R458`（实况 139/R476）⇒ 以 registry + 本轮计划/报告为准。
