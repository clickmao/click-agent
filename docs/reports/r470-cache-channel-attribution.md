# R470 报告 · 真实流量的命中归因通道：K2b 在真实流量上 100% 不适用

- 轮号: R470（口径补全 + 打点接线；**零压缩/注入策略改动**）
- 计划: `docs/plans/v0.87.0-r470-cache-channel-attribution.md`
- 外部真值: `data/telemetry/host.jsonl`（**真实远端调用遥测**，非桩）`sha256=2a9e34490b2d92e776d5a9c364daa64adc9168cbc9bc69a1787bf2438cd59a13`，`point==llm_call` **43 条**
- 器具: `eval/rover/r470/real_calls.py`（独立双实现 + 判据机检）→ `real-calls.json` / `asserts.json` / `negctl.json`；产品侧 `PromptCacheKpi.ChannelFields` + `src/agent.tests/PromptCacheChannelTests.cs`（**同规则、不同实现，互为对照**）
- 证据命令: `python3 eval/rover/r470/real_calls.py`（退出码 0 = 全绿）；`dotnet test ... --filter PromptCacheChannelTests|PromptCacheKpiTests|VerificationFormTests|DevPlanDocRefTests`

## 1 因果链
用户 KPI（一轮任务总 token ↓≥30%）→ 唯一能量化「前缀被复用、新算变少」的指标 = prompt 缓存命中率（K2b）→ **机检 43/43 真实调用的 `effective_hit_rate` = -1（100% 不适用）** → 但供应商侧**确实在命中**（32/43 命中 > 0，命中量 2,048~2,304）→ 收益客观存在却**无度量、无驱动信号** ⇒ 本轮补「跨会话共享前缀」归因通道（**只增不改**：既有 `cacheable_tokens`/`effective_hit_rate` 与 97% 红线一字未动）。

## 2 读数（43 条真实远端调用）
### 2.1 归因与命中
| 通道 | 调用数 | 命中 > 0 | 命中量直方图 | 该通道命中率 |
|---|---|---|---|---|
| `shared_prefix`（无同会话前驱） | **43** | **32（74.4%）** | 2048×19, 2176×7, 2304×2, 256×2, 127×2 | min 0.1666 / 中位 0.4086 / max 0.7079 |
| `same_session`（有同会话前驱） | **0** | — | — | 无样本 |
| `unknown` | 0 | — | — | — |

- 全量：`hit = 59,518 / prompt = 130,974` ⇒ **命中占比 45.44%，新算 71,456 tok（54.56%）**。
- 命中量**饱和在 2,048~2,304**（= 64-token 单元的整数倍）；共享前缀 ≈ **2.0k~2.3k tok**（观测饱和值，非上界证明）。
- 非 64 对齐例外 **2 条**（`hit=127 / prompt=261`，`agent_session` 为空），逐条列于 `asserts.json.unaligned_hits`，未静默过滤。

### 2.2 分档（真实调用）
| 档 | n | prompt 中位 | 命中中位 | **新算中位** | 命中占比中位 |
|---|---|---|---|---|---|
| A `<400`（冷启动短调用） | 13 | 232 | 0 | 230 | 0.0% |
| B `2.9k~3.1k` | 14 | 3,037 | 2,048 | **1,020** | 66.75% |
| C `5.2k~6.4k` | 16 | 5,479 | 2,176 | **3,320** | 39.15% |

⇒ 共享前缀（≈2k）**不随 prompt 增长**：C 档调用每次真金白银新算 **3,320 tok**（占 prompt 61%），是本 KPI 的分子主来源。

### 2.3 判据（`asserts.json`，逐条机检，全绿）
| 判据 | 内容 | 取值 | 结果 |
|---|---|---|---|
| C1 | 真实 `llm_call` = 43（BOM 行不得被吞；`utf-8` 会静默少 1 行） | 43 | OK |
| C2 | 归因守恒：`shared_prefix=43 ∧ same_session=0 ∧ Σ=43` | `{"shared_prefix":43}` | OK |
| C3 | 通道非空：命中 > 0 ≥ 30 | 32 | OK |
| C3b | 直方图逐值 == 报告 | `{127:2,256:2,2048:19,2176:7,2304:2}` | OK |
| C4 | 非 64 对齐命中逐条列出 | 2 条，`hit=127` | OK |
| C5 | K2b 可测性裁定：同会话前驱 0 ⇒ `eff=-1` 43/43 | `{same_session_predecessors:0, eff_-1:43}` | OK |
| C6 | 负控 a/b/c 全绿 ∧ **d（归因规则反写）原判据必须不成立** | 4/4 true | OK |

代码侧（`PromptCacheChannelTests`，8 个用例，含真实夹具回放 / 禁双计 / 未上报≠0 / 溯源子集 / 负控反写）与脚本侧**双实现互证**：`real_calls.py` 全绿退出码 0，`dotnet test` **29/29 通过**（含 `VerificationFormTests`+`DevPlanDocRefTests` 形式门禁）。

## 3 交付物
| 文件 | 作用 |
|---|---|
| `src/agent.modelqueue/PromptCacheKpi.cs:104-141` | 新增 `Channel`/`SharedPrefixHitTokens`/`SharedPrefixHitRate`/`ChannelFields`（只增不改） |
| `src/agent.modelqueue/ModelQueueRouter.cs:714,735 / :826,834 / :901,909` | 三处 data-carrying `llm_call` 打点均铺 `cache_channel`/`shared_prefix_hit_tokens`/`shared_prefix_hit_rate` |
| `src/agent.tests/PromptCacheChannelTests.cs` | R470 语义/禁双计/真值回放/负控/溯源 8 例 |
| `src/agent.tests/PromptCacheKpiTests.cs` | 接线断言加强为三元组（R377+R380+R470），三处逐一配对扫描 |
| `eval/rover/r470/{real_calls.py,real-calls.json,asserts.json,negctl.json}` | 真值夹具 + 判据机检 + 负控 |

**AOT 形态自证**：`dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/r470_publish` ⇒ 生成 `agenthost`（ELF 64-bit, 动态依赖仅 `libc/libm/vdso`，**无 libcoreclr/libhostfxr** ⇒ 原生形态）**15,343,232 B**；**IL 警告 0**（日志仅 2 条既存 `NU1510` NuGet 提示）。

## 4 诚实边界
- **未发起新的真机远端调用**（配额/凭据风险）⇒ 全部读数来自**已有** 43 条生产遥测，样本量小；「共享前缀 ≈2.0k~2.3k」是**观测饱和值**，不是上界证明。
- `shared_prefix` 的**因果不可分**：跨会话前缀复用 vs 提供方同文本缓存，同一 token 数下无法区分 ⇒ 通道命名与文档均按「共享前缀」表述，不宣称机制。
- **未测**：命中是否真的在计费上打折（提供方计费口径未取到）⇒ 「命中 ⇒ 省钱」这一步仍只是**未验证前提**；长会话（同会话第 2 轮起）真实命中率**仍无真实样本**（`same_session = 0`）⇒ 97% 红线的真机可达性仍只有 R469 的离线界。
- **未做**改前 AOT 体积对照（本轮为纯新增打点，未测体积差）；`cache_hit_rate` 旧口径字段与 `effective_hit_rate` 语义未动，`scripts/kpi_cache_hit.py` 聚合器**尚未**纳入新通道（列下轮）。

## 5 下轮候选
1. **R471 聚合器纳入通道**（小、确定）：`scripts/kpi_cache_hit.py` 汇总 `cache_channel` 分通道报数 + `shared_prefix_hit_rate` 红线（否则新字段落盘无人聚合 = 空心）。
2. **R471/R472 真机靶点：C 档新算 3,320 tok 的组成分解** —— 需要一次「同 prompt 结构」的真机/桩侧全量 `messages` 抓取，把 5.4k 拆成 `共享前缀 2.1k + 会话私有 3.3k`，再判定 3.3k 里有多少是**稳定内容被放在了私有段**（= R469 结论的「升前缀」直接可执行化）。
3. **红线口径迁移**：把「97% 单值红线」改为「分档上限 + 达成轮占比」，并按通道分别设红线（`same_session` 维持 97%、`shared_prefix` 先设观测基线 39%~67% 档），避免真实流量上红线恒"不适用"。
