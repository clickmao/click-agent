# R467 报告 — 分母固化：远端调用分解台账 + 臂可比性闸 + 同二进制「判官标志」复现裁决

- 日期: 2026-09-16 · 计划: `docs/plans/v0.84.0-r467-denominator-pinning.md`（预注册判据 C1–C6 跑测前落盘）
- 性质: **测量完整性轮**（不改任何 `src/**` 链代码 ⇒ 无 AOT 重发布；被测二进制 = R466 AOT 产物，
  `sha256=9f5f9e696da8b8d5b06f54ca741463c13e2a43b4f472c1876a62ca6dcb5ac7c2`，`/tmp/pub_r466/agenthost`）
- 一句话: R465→R466 的分母漂移（21/33,323 → 13/32,097）**真因是臂脚本的 `relation_judge` 标志**，
  不是产品路由不确定性；判官本地化本身值 **8 次远端调用 / 1,226 tok**，且该差异**逐位吻合**。

## 1. 因果链（依据 → 推论 → 后果）

1. 产品代码里产生「真有远端调用的判官」的唯一路径 = `RelationJudgeEnabled != true`
   （`ModelQueueRouter.cs:330`，调用点 `IndustrialAgentV2.cs:1843`）。
2. 两侧桩日志逐条比对：R465 `Arole` 有 8 条判官形调用（`sys=8字`、`prompt≈145 tok`），R466 `Arole` 同位置 0 条；
   两轮判官事件都是 12 条，其中 4 条 `prompt_len=0`（机械短路，零请求）。
3. 而脚本自身 R465 `run_arm.sh:43` = `RJ=false`、R466 `run_arm.sh:39` = `RJ=true`
   ⇒ **假说 H1：漂移 = 臂定义漂移**。
4. 后果：台账**没有路由字段**，同名臂「Arole=稳定分母」的前提可在两轮间静默失效而无人察觉
   —— 用户口径要求「同题优化前后对比」，分母漂移使该对比不成立。

## 2. 本轮产出（真实读数，全部机检）

同二进制 / 同桩 / 同网格 `p12` / 同 role 夹具（`skeptic-growth.rbin`，`sha256=ecb75f53…`）；
RUNDIR 字面长度配平 ⇒ 复现判据用**精确等值**，不需 Δchar 折算。

| 臂 | 门 | relation_judge | calls | total tok | 分解（主/判官/微） | 判官路由（本地/真远端/短路） | turns_ok | 期望 | 结果 |
|---|---|---|---|---|---|---|---|---|---|
| `Arole`(=r466 Arole) | off | **on** | **13** | **32,097** | 12/0/1 | 8/0/4 | 12/12 | 13/32,097 | ✅ 逐位复现 |
| `Aroff`(=r465 Arole) | off | **off** | **21** | **33,323** | 12/**8**/1 | 0/8/4 | 12/12 | 21/33,323 | ✅ 逐位复现 |
| `R`(=r466 R) | on | on | **6** | **14,529** | 6/0/0 | 8/0/4 | 12/12 | 6/14,529 | ✅ 逐位复现 |
| `R2`(=r466 R2) | on | on | **6** | **14,531** | 6/0/0 | 8/0/4 | 12/12 | 6/14,531 | ✅ 逐位复现 |

- **单变量裁决**：`Aroff − Arole = 8 次远端调用 / 1,226 tok`，而桩侧这 8 条判官调用实测
  `prompt 1,170 + completion 56 = 1,226 tok` ⇒ **逐位吻合**（不是估计、不是折算）。⇒ **H1 被证实**。
- **分母裁决**：生产面 `base/models.yaml` 是 `turn_gate: true` + `relation_judge: true`
  ⇒ **生产等价分母 = 13 / 32,097**；R465 的 21/33,323 是「判官未本地化」的历史配置，**不是分母**。
- **KPI（同题、固定分母）**：`1 − 14,529/32,097 = 54.73%`；若坚持沿用 R465 口径 = `56.40%` ⇒ **两种口径都 ≥30%**，
  且远端调用次数 `6 vs 12`（主调用）/`6 vs 21`（含判官）—— 省下的最大单项就是 8 次判官远端调用。

### 2.1 器具交付（本轮实交付物）
- `eval/rover/r467/settle_r467.py`：在 R466 结算器上增列 **`calls_class`**（桩侧逐条分类 main/judge/micro/other）、
  **`judge_route`**（`events/local/shortcircuit/remote_real/remote_fallback` + ms + prompt_len）、
  **`remote_llm_events`**（宿主 `llm_call` 点数 = 内部计数）、**`flags-<ARM>.json`**（生成后 config 解析 + env 声明 + 二进制/配置/role sha + 字面 cwd）；
  每臂落 `ledger-<ARM>.json`，全局落 `verdict-r467.json` + `gate-audit.json`。旧读数字段语义不变（跨轮可 diff）。
- `eval/rover/r467/denominator_gate.py`（新闸，fail-closed）：G1 分解恒等式 · G2 内外一致（桩 vs 遥测）·
  G3 路由干净（`rj=true ⇒ remote_fallback==0 ∧ local>0`；`rj=false ⇒ local==0 ∧ remote_real>0`）·
  G4 **同名臂跨轮标志必须逐键同**（不同 ⇒ 该臂读数 `VOID_NOT_COMPARABLE`，不同名异类 ⇒ `NA` 拒绝背书）·
  G5 声明完备（本轮台账缺任一行为键 ⇒ 红）。`arm_class` 单一来源 = `arm_class_of()`（settle 直接 import，禁止两处各写一份）。
- `gate-selftest.json` **3/3 通过**：S1 用**真实历史** R465 台账当生产等价分母 ⇒ 判红（差异键恰为 `relation_judge`）；
  S2 人为破坏恒等式 ⇒ 判红；S3 只改器具 sha ⇒ 判绿（不把二进制换代误判成分母漂移）。
- `gate-audit.json`（事后）：X1/X2 同名臂跨轮（R466→R467）可比 ✅；X3 同类分母跨轮异名（r465.Arole→r467.Aroff）可比 ✅；
  X4 真实漂移负控被判红 ✅。

### 2.2 执行证据（测试面，全量无 filter）

| 项 | 命令 | 读数 |
|---|---|---|
| 形式门禁（登记行/计划引用，本轮新增 2 行） | `dotnet test ... --filter "FullyQualifiedName~VerificationFormTests\|FullyQualifiedName~DevPlanDocRefTests"` | **Passed 9 / Failed 0**（执行数 9 > 0 ⇒ 真跑，非 rc=0 空跑） |
| 全量首跑 | `dotnet test src/agent.tests/agentframework.tests.csproj -c Release` | **1410/1411**（1 例红：`TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure`，`Assert.Contains` 未命中 `pre_boot_probe`） |
| 该例隔离跑 | 同上 `--filter "FullyQualifiedName~TelemetryPendingTests"` | **2/2 绿**（42 ms） |
| 全量复跑 | 同上（无 filter） | **1411/1411 绿**（34 s） |

- 判定：**既有偶发 flake**，与 R467 改动面（`docs/**` + `eval/rover/r467/**`，未碰 `src/**`）无交集；
  机制 = `AgentTelemetry` 是**静态类**（测试注释自述「测试间共享状态」），`Emit` 先于 `Configure` 时进 pending ring，
  并行/顺序变化会让 `pre_boot_probe` 落进别的 writer ⇒ 该断言对执行顺序敏感。**本轮不隐瞒、不抹平**，列为下轮候选。
- 状态：本报告出具时全量 = **1411/1411 绿**（复跑）；首跑那 1 例红如实记录在案。

## 3. 预注册判据逐条结果（跑测前落盘，未改写）

| 判据 | 内容 | 结果 |
|---|---|---|
| C1 | 分解恒等式 4/4 臂 | ✅ pass |
| C2 | 桩侧 calls == 宿主 `llm_call` 事件数 4/4 | ✅ pass |
| C3 | Arole = 13 / 32,097 / turns_ok 12 / 路由 8L+0R+4short | ✅ pass |
| C4 | Aroff = 21 / 33,323 / 路由 0L+8R+4short（H1 直接判决） | ✅ pass |
| C5 | 闸负控三条（真实历史红 / 构造红 / 合法绿） | ✅ pass 3/3 |
| C6 | R = 6/14,529、R2 = 6/14,531、Δtok=+2、判决面+答复逐位同 | ✅ pass |
| C7* | 分母可比性审计 X1–X4 | ✅ pass（***事后增补**，不在预注册 §4 内，强度只作器具回归证据） |

## 4. 诚实边界（没测到的就说没测到）

1. **`shortcircuit`（4 条 `prompt_len=0`）的机制未查明**。器具只按可观测口径计数：
   这 4 条既非远端调用（桩日志 0 条对应），也非本地调用（本地判官数正好 8）⇒ 只能是零请求判定路径。
   其内部触发条件未定位，未做进一步断言。
2. **C7 是事后判据**：期望值是在看到 R467 读数之后设定的（X1/X2/X3 绿、X4 红），
   因此它只能证明「闸的回归行为符合设计」，不构成对漂移的独立证实（H1 的证据是 C3/C4 的逐位复现）。
3. **历史重建台账的两个键「不可核」**：`repeat_priority`、`role_sha256` 在 R465/R466 的脚本里未声明
   ⇒ 这两键的跨轮一致性只能从 R467 起核；旧轮次**不能**声称已核。G5 只对当前轮强制完备。
4. **延迟代价真实存在、且非确定**：判官本地化把 8 次调用从 ~42 ms（远端）移到本地；
   R467 实测本地判官 `40.0 s → 126.6 s`（R466 实测 `58.2 s → 144.1 s`）—— 累计等待形态，逐轮递增，
   两次运行不等值 ⇒ **token 面收益（确定，1,226 tok/轮）与延迟面代价（时序相关，未优化）必须分开记**。
   本轮**没做**延迟优化，也**没给**「延迟可接受」的结论。
5. **真实流量未复验**：R449/R452 的 state.db 1542 轮真实流量门 `r1=0/Skip=0 ⇒ 降幅=0`，
   本轮未重跑该面 ⇒ 「单轮 token 降 ≥30%」目前仍是**同网格 p12 受控题面**上的结论 + 历史真实流量上的「守卫承重」结论，两者不可互换。
6. **AOT 面本轮为空**：未改 `src/**` ⇒ 无重发布、无 IL 警告读数；报告的 AOT 证据仅 sha 归类（复用 R466 产物）。
7. `P4`（Δtok 归因律修正）：R466 写的「Δchar×2」**不是律**，只是该实例的巧合；
   实测律 = 工作区根路径出现在每次调用的 system 首条，每次调用 δ∈{0,+1}（分词边界）⇒ 本轮 R/R2 复测仍为 +2。

## 5. 下轮候选（按杠杆排序）

1. **判官本地化的延迟面**：8 次判官 ×~12 s 全部落在本地串行队列（`local_ms` 递增 ⇒ 排队形态）。
   候选：判官与门共用同一常驻端口时按优先级/批处理合并（R448 候选②「合并 judge 与门」的量化版）；
   判据面 = `local_ms` 首末值 + 门控轮稳态延迟，**不得**用 token 面代替延迟面。
2. **真实流量复验（state.db 1542 轮）**：用 R467 的 `calls_class` 分解把真实流量的 0 降幅拆开
   ⇒ 判定「守卫承重」到底承在哪一类调用上（预注册：分解恒等式 + 守卫命中率）。
3. **前缀按需注入**（97% 缓存红线相关）：主调用 prompt 逐轮单调增（2,019→3,461 tok）是当前最大单项成本；
   与判官无关，需独立器具面。
4. **未声明键回填**：把 `repeat_priority`/`role_sha256` 之类器具键写进历史轮脚本的 flags 生成器（只对**未来**轮生效），
   并把 R467 的 `arm_class_of()` 提到共享位置（现已在 `denominator_gate.py`，供后续轮 import）。
5. **既有 flake 收口（与主线无关，但属「不得静默」项）**：`TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure`
   依赖 `AgentTelemetry` 静态类的 pending ring，对执行顺序敏感（首跑 1 红 / 隔离 2 绿 / 复跑全绿）。
   候选：把该断言改成**进程内隔离**（per-test 唯一 pending ring 注入）或显式串行化，判据 = 连续 3 次全量 1411/1411；
   **不得**用「复跑就绿」当已修。
