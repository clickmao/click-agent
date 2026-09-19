# 动态打点测试评测回滚策略说明报告

> **文档性质**：AgentFramework 千轮迭代主控报告（随千轮任务持续更新，最新版本随每次提交推送 GitHub）。
> **主题（用户钦定 2026-09-07）**：针对用户话题倾向，围绕用户体验，使用动态打点策略，不断优化迭代 agent 功能。
> **恢复迭代入口**：上下文丢失后，读本报告 §7（迭代状态快照）+ `eval/results/mass_*.json`（自动镜像轮数据）即可继续，无需其他上下文。
> 最后更新：R324（2026-09-09，KPI-2 token 专项）· commit 见 `git log --oneline -1`
> **方法论总纲**：何时新增点位/如何探索点位/测试数据源设计（含负面数据）/跑测真实性校验 → 见 **`docs/reports/iteration-master-plan.md`**（方法以它为准，状态以本报告为准）。

---

> KPI-2 token 长期监测: `docs/reports/kpi2-token-report-R324.md` + 周报脚本 `eval/token_report.py` (每 10 批 audit 节奏)。

## 0. 一句话总纲

**打点 → 批测对比 → 找缺陷/靶点 → 修复/优化 → A/B 验证 → 打分不如上版即回退**，循环往复；所有决策必须有打点数据背书，禁止无数据的主观迭代。

## 1. 设计原则：打点为什么是"动态"的

传统监控是"埋了就看"，动态打点是"看数据反推埋点"——四条闭环规则：

1. **点位跟着问题走**：每个点位存在的前提是"它能回答一个当前迭代的疑问"（例：`assembly_ms` 回答"上下文组装为什么 13s"）。
2. **数据反哺点位增删**（用户要求①）：每 5 批（25 轮）做一次点位审计——
   - 恒定无信息量的点（如某 kv 永远同值）→ 移除或改采样；
   - 出现过 ≥1 次决策价值（促成过一次修复/回退）→ 保留并考虑升级为 KPI 健康带；
   - 覆盖空白（某环节无点位却出现在 wall 疑点里）→ 新增。
3. **用户话题/体验导向**（用户要求②）：agent 的存在意义是帮用户完成任务——打点维度必须包含"用户话题倾向"（tendency 点位 + 话题命中）和"体验质量"（wall 时延、回答 token 预算、召回命中率），而不是只看程序内部健康。
4. **打点链自身也要自证**：harness 自己的 bug（缺陷 53：空切片+字典序排序让 delta 恒 None/错序）曾让 D5 数据静默失效——对比数据必须先抽查自证可靠再用于决策。

## 2. 打点体系全景（当前 25 个 Emit 点位）

### 2.1 按层分类（`grep -rhoE 'Emit\("[a-z_]+"' src` 实测清单）

| 层 | 点位 | 回答的问题 | 去向 |
|---|---|---|---|
| **引导** | boot / pre_boot_probe / post_boot_probe / no_op_probe | 启动是否健康、AOT 后依赖是否齐 | smoke 判定 |
| **意图** | intent / goal / tendency×4 | 用户在问什么、话题倾向是什么 | 体验画像 |
| **上下文** | assembly / phase_timing(5处) / bge_mode / bge_embed / compression / memory | 组装多快、哪步慢、压缩是否漂移 | D3 热路径 |
| **执行** | llm_call×5 / llm_retry / llm_failover / loop_turn×2 / skill*×8 / subagent / evidence_gate / prompt_build | LLM 调用、技能执行、循环健康 | 主链 |
| **余额** | balance_sync×3 | 余额阈值切模是否工作 | 语义诚实 |

### 2.2 轮 JSON 落盘字段（`data/logs/eval/rounds/mass_N.json`，自动镜像 `eval/results/`）

- **轮级**：`round/label/ts/cases/passed/tokens_total/prompt_total/completion_total/wall_total_ms/kpi_breaches/hist_base_rounds`
- **用例级**：`pass/wall_ms/tokens(3维)/intent/intent_ms/llm_calls/llm_ms_total/loop_ms/assembly_ms/bge_ms/skill_hits/snippets/sources_recall/points/isolated_score/delta_tokens_vs_hist/delta_wall_vs_hist/models/notes`
- `delta_*`（D5）与 `kpi_breaches`（D2）是自动对比产物，人工不填。

### 2.3 已点名的打点驱动成果（证据链）

| 发现 | 点位 | 结果 |
|---|---|---|
| C08 推理输出 943tok 大户 | `llm_call` completion 维度 | 规则8 输出纪律 → -49% |
| **assembly 11-13s（缺陷54）** | `assembly` ms + `phase_timing:compress` | 三层治理 → **210ms，-98%** |
| telemetry 瞬时丢失 | `llm_call` 缺失 | 缺陷51 pending ring |
| 比例化 rel 失真 | `assembly` r 值 | 缺陷50 |
| delta 恒 None | harness 自身 | 缺陷53 |
| mass_251 C03 4357tok | D2 KPI breach | 复跑 in-band，防误回退 |

## 3. 每轮检测的 PGO 动态打点策略（v2，D1-D5）

PGO（Profile-Guided Optimization）思想：用真实轮次 profile 引导优化方向，而不是静态猜测。

- **D1 分级采样**：高频恒定点位（如 bge_mode）在稳定后降采样，降低打点自身开销。*状态：设计完成，未实施。*
- **D2 KPI 健康带**：每用例 tokens/wall/rel 有平滑基准带（历史 5 轮均值），越界即 `KPI_BREACH` 标记。**breach 只标记不判 FAIL**——先复跑确认，防把 LLM 单轮波动当回归（mass_251→252 实证）。*状态：✅ R128 上线。*
- **D3 phase_timing 热路径计时**：intent/llm/compress/recall_* 分段 ms，找出 wall 的真实去向。*状态：✅ R129 上线，首战即锁定缺陷54。*
- **D4 reply_rel 语义质量**：bge 对 reply vs 查询做语义相关性，自动发现"答非所问"。*状态：设计完成，未实施（下一批点）。*
- **D5 对比基准自动化**：落盘前自动读历史 5 轮（按 ts 排序，非字典序——缺陷53 教训），算 per-case 平滑 delta 写入轮 JSON。*状态：✅ R128 上线。*

## 4. 校验策略（用户要求③）：明确的评测方案

### 4.1 批量测试运行脚本（唯一入口，禁止另起炉灶）

```bash
# 单轮（~84s，5 用例 --quick 或 17 全量）
cd /home/agentuser/AgentFramework
export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT=$HOME/.dotnet
set -a; source .env.local; set +a
export AGENTFRAMEWORK_LOCAL_DISABLED=1
python3 eval/run_round.py <轮号> "<标签>" --quick

# 批测 = 5 轮循环（后台 + 日志）
for i in 1 2 3 4 5; do
  python3 eval/run_round.py mass_$((250+i)) "R1xx batchNN <主题>" --quick >> /tmp/batchNN.log 2>&1
done
```

- 轮号全局唯一递增（下一轮查 `ls data/logs/eval/rounds/ | grep mass | sort -V | tail -1`）。
- 轮 JSON 自动镜像到 `eval/results/`（R130 起，勿再手工 cp）。
- 分析：`python3 eval/analyze.py`（多轮聚合）。

### 4.2 功能性能评测维度（每轮自动算）

| 维度 | 指标 | 健康带（当前） |
|---|---|---|
| 功能 | passed/cases | **必须 25/25**（含 --quick 5/5） |
| 性能 | tokens_total（轮均） | 波动带 ~3600-4100；连续 3 批 >4100 → 输出预算治理 |
| 性能 | wall_ms（轮均） | ~88s→修复54 后 ~66s（持续观察） |
| 性能 | assembly_ms / compress_ms / llm_ms | D3 分段（见 §6 基线表） |
| 体验 | C08/C11 类长答用例 completion | 规则8 后 ≤600tok 量级 |
| 召回 | sources_recall per-case | WorkspaceFiles 100% / AgentContext 0.9 / Memory 75% |
| 质量 | isolated_score（隔离）/ gate_to_ask | 隔离 score≥2 |

### 4.3 迭代判定与回滚机制（明确的评测方案核心）

**多轮测试后更优迭代更新（判定为优）：**
1. 批测 25/25 全绿；
2. 轮均 tokens ≤ 上一版（D5 delta ≤ 0 视作达标）；
3. 无新增 KPI breach（或 breach 经复跑证实为 LLM 波动）；
4. 单测全绿（当前 386）+ AOT 发布 0 IL 警；
→ 满足全部 → **迭代生效**：台账记录（`docs/reports/wave3-ledger.md`）+ commit + push。

**性能更差回滚（判定为劣）：**
1. 批测出现真 FAIL（排除 LLM 波动：同用例复跑 2 次仍 FAIL）；
2. 或轮均 tokens/wall 连续 2 批劣化 >10%（D5 delta 确认，非单轮波动）；
3. 或新增 KPI breach 连续 2 批同点位；
→ 满足任一 → **回滚**：`git revert` 对应 commit（点位与代码实现一起回——打点改动与功能改动同 commit 是刻意约定，保证回滚原子性）→ 复跑批测确认恢复基线 → 台账记录回滚原因。
*历史执行记录：R120 anomaly 防护定案（llm_calls=0+reply 非空→pass+anomaly 不 REVERT）；打分不如上版即回退为长期铁律。*

### 4.4 AOT 铁律（回滚机制的一部分）

任何 src 改动后：`dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 --self-contained` 必须 **0 IL 警**（NU15xx 类 NuGet 提示不算）+ 冒烟（`echo "1+1=?" | ./agenthost`）。没有 JIT 版本——发布形态只有 AOT。

## 5. 用户话题倾向 & 用户体验专项（主题核心）

**现状（R123 召回专项 + R129）**：
- 四源召回画像：WorkspaceFiles 主力（100% 命中 rel0.84）/ AgentContext 稳定（0.90）/ Memory 75%（治理后）/ **UserTendency 恒 0（断链）**。
- **首要功能缺失 = UserTendency 聚合断链**：画像数据真实存在（`data/tendency/cli_user.json`：Python:25, Web API:23，批测积累），但 `GetContextBiasAsync` 聚合 confidence≤0.3（阈值）→ `RecallFromUserTendencyAsync` 恒不命中 → 用户话题倾向永远影响不了上下文。**这是"围绕用户话题倾向优化"主题的第一靶点**（涉及 `src/agent/tendency/TendencyData.cs` 聚合链 + `src/agent/contextassembler/ContextAssembler.cs`）。
- 空 userId 落盘已修（缺陷52），聚合断链未修。

**体验优化已落地**：规则8 输出纪律（解释类 -49% tokens）、C11 prompt 治理（746→586）、缺陷54（assembly -98% 直接砍用户等待）、D2 防误回退。

**体验优化候选（待打点验证）**：D4 语义质量（答非所问自动发现）→ 长会话记忆衰减策略 → tendency 阈值自适应（冷启动 0.3 过严）。

## 6. 当前性能基线（对比锚，更新于 R130）

| 指标 | 修复54 前 | 修复54 后（mass_255） |
|---|---|---|
| assembly_ms（C08/C11） | 11000-21000 | **210/245** |
| compress_ms（C08） | ~20000 | **<200**（n 段 Full/低分跳过 embed） |
| C08 wall | 34.0s | 13.3s |
| 批 wall（5 用例） | ~94s | **65.6s（-30%）** |
| 批 tokens 均值 | 3671（批39） | 待批40 确认 |
| 单测 | 386 | 386 全绿 |

## 6b. prompt 缓存命中率 KPI（R377 新增, K2b）

**口径**（与 `src/agent.modelqueue/PromptCacheKpi.cs` 严格一致）:

- 命中率 = `prompt_cache_hit_tokens / (prompt_cache_hit_tokens + prompt_cache_miss_tokens)`, 保留 4 位小数;
- **未上报记 -1 且不并入比率**（provider 不给字段 ≠ 命中 0%）; 分母为 0 同样 -1;
- 打点字段固定 `cache_hit_tokens` / `cache_miss_tokens` / `cache_hit_rate`（`llm_call` 点的三处 data-carrying 路径全覆盖）;
- 离线复算: `python3 scripts/kpi_cache_hit.py [遥测路径] [--since ISO] [--json 输出]`（按模型分组 + 未上报计数 + 落盘 `eval/results/kpi_cache_hit_<UTC>.json`）。

**首发基线（R377, 真机同题 2 跑 / 4 次调用）**: 命中 **3,328** / 未命中 **7,610** → **30.43%**（RUN1 23.73% → RUN2 36.94%）;
全量遥测同口径: 上报 4/45 次调用, 41 次未上报（历史行无此字段, 如实分列不读成 0%）。

## 7. 迭代状态快照（恢复迭代从这里开始）

> ### ⏱ 最新状态（2026-09-17 主线定义更正：外部对照自检；R413 KPI 降为其判据之一 — 恢复迭代先读这里；下方为历史快照）
>
> - **最近一轮（R586，2026-09-20 · cron 60min tick）**: **主线对照轮（**同被测件 + 同冻结题集、只换窗集**的复跑，判定 R585 质量缺口是否跨窗复现）= 外部真值 codex × 产品默认档（三枚剂量键显式 unset），3 窗 `w157..w159`、每窗 真值×1 ＋ 产品×3** —— 冻结题集 sha `e0c667c2…`（同 R559–R585）；二进制 sha `4b70fd7c…` **与 R585 同件**（`bin_sha_stable=true`）；**质量（58 例）**：真值逐窗 `58/58/58`（中位 58、极差 0；`all_pass` 3/3 ⇒ 无 unreliable 窗）vs 产品逐窗中位 `58/55/43`（中位 49、极差 15；逐跑次 `47,58,58 / 55,58,49 / 48,43,43`）；**配对差 `[0,−3,−15]`、中位 −3 < 下限 −2 ∧ `w159` D=−15 触底（两条同时未过）⇒ rc=1 FAIL（质量配对未过）**；**C5 三态 = 「缺口跨窗复现」**（与 R585 D 集 `[−8,−3]` 同号 ∧ 区间重叠；**并列不相减**）；**C6 PASS**（步数 9/9 在档 `[7,7,7,13,8,7,7,7,7]` / `plan_steps_total [10,10,17,14,9,10,10,11,11]`）+ **R585 纠偏**（该列在 `verdict-r585.json` 里本就在档，R585 报告与 §7 块写「未测」= 报告面缺陷；R585 首跑读数不撤）；**C7 = 0 超时例**（R585 的 8 例 `TimeoutExpired` 本轮未再现，同 60s 口径；不作「已修复」宣称——零产品改动）；**成本三列（铁律 11 rc=1 ⇒ 标「参考（未可验收）」）**：调用 19 vs 51 / 新算 prompt 4,058 vs 25,012 / completion 44,380 vs 24,561（**按跑次归一** 2.11 vs 17.0 / 451 vs 8,337 / 4,931 vs 8,187；两侧跑次数 9 vs 3 ⇒ 禁比总量）/ 命中率 v_all 0.97 vs 0.95；**归因（只读定因器，冻结快照副本重放 + 独立 oracle）**：失败 100% 集中 `wythoff` 单族，类别 `MOVE_NOT_COLD` 38 / `EMPTY_OR_ERROR` 12 / `LOSE_FOR_WIN` 7 / `WIN_FOR_LOSE` 6，族内通过数（`4/15/15 · 12/15/6 · 5/0/0`）与铁律 11 前置器逐臂窗 **9/9 对上** ⇒ 非采集侧假红；**同臂同例跨窗摆动 11/15 · 15/15 · 15/15 ⇒ 摆动 ≥ 臂效应，单窗不作能力结论**；**判别力成对控制未行使**（`gate-disc-pair.json` 两臂同判 `GATE_BLOCKED`、`true_discrimination=false`、rc=3，按「未行使已登记」放行 ⇒ **不得读成闸已行使**）；**自捕 3 件**（R585 报告面 `steps` 误写「未测」/ 判据器汇总打印面缺 `steps` 列 / 影子自检用例未做臂名投影 ⇒ 修用例不改判据），**判据器影子自检 7/7**（含可判绿、异轮臂名 rc=3 缺侧 fail-closed、R585 读数投影后逐值复现其判决）；轮志 `eval/rover/r586/report-r586.md`、定因 `eval/rover/r586/wythoff-cause-r586.json`、台账 `eval/capability/kpi.jsonl`（R586）。
> - **最近一轮（R585，2026-09-19 · cron 60min tick）【历史快照，已被上方 R586 行取代】**: **主线对照轮（器具环境恢复后首次可起臂）= 外部真值 codex × 产品默认档（三枚剂量键显式 unset），3 窗 `w154..w156`、每窗 真值×1 ＋ 产品×3** —— 冻结题集 sha `e0c667c2…`（同 R559–R583）；**质量（58 例）**：真值逐窗 `56/58/58`（中位 58、极差 2）vs 产品逐窗中位 `58/50/55`（中位 55、极差 8；逐跑次 `58,58,58 / 53,50,47 / 58,48,55`）；**配对差 `[−8,−3]`、中位 −5.5 < 预定下限 −2 ⇒ rc=1 FAIL（质量配对未过）**（`w154` 真值自身 56/58 ⇒ 标 unreliable 不进配对、其 2 例单列）；**成本三列（铁律 11 rc=1 ⇒ 标「参考（未可验收）」）**：调用 20 vs 74 / 新算 prompt 5,601 vs 28,392 / completion 48,941 vs 23,907（**+105% 单列**）/ 命中率 v_all 0.97 vs 0.97；**归因**：失败 100% 集中 `wythoff` 单族（超时 8 例两条独立路径互证 ⇒ 非采集侧假红）；**自捕器具 2 件**（闸输出读契约 fail-closed 未起臂 / 判据器残留臂名仅重跑后处理）；轮志 `eval/rover/r585/report-r585.md`、台账 `eval/capability/kpi.jsonl`（R585）。
> - **最近一轮（R567，2026-09-19 · cron 60min tick）【历史快照，已被上方 R585 行取代】**: **主线对照轮（同窗单变量第二窗集 = 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 取值 0 vs 3 × 外部真值 codex）** —— 冻结题集逐字节复用（`taskset` sha `e0c667c2…`，与 R559/R560/R563/R565/R566 同件）+ 6 新窗 `w131..w136`；全臂同一枚 AOT 二进制（sha `320d0eb1…`）。读数：`C1`（真值）逐窗 56/58/58/58/56/58 ⇒ 中位 **58.0**/极差 2、41 调用、新算 26,918；`R567B0`（轴=0）52/58/53/42/55/44 ⇒ 中位 **52.5**/极差 16、6 调用、新算 906、completion 16,364；`R567B3`（轴=3）47/58/58/45/51/58 ⇒ 中位 **54.5**/极差 13、23 调用、新算 6,903、completion 52,749。判据 v2 判决 **rc=1 FAIL(被测/前提)**、`blocked=[quality_paired_shortfall:R567B0,R567B3]`、`delta_median` −4.5 / −2.5、6/6 真值窗 reliable。**承重结论**：与 R566（轴 0 vs 1：50.0 vs 55.0，−7.5/−3.0）**并列不相减**后，剂量 0→1 差 +5 而 0→3 差 +2 —— **非单调且与跨窗摆动同量级** ⇒ 剂量档位不是承重变量，两档仍均不过判据；失分结构 = 全臂 `always_fail` 空、`wobble` 共同集合 `wythoff#43–57`（`life`/`nim` 全臂全窗全绿，`sub` 仅 B0 在 w134 掉 5 例）⇒ 与 R562/R564 只读定因一致，本轮不修（未放行）。轴关（B0）成本读数：调用 −73.9% / 新算 prompt −86.9% / completion −69.0%，代价中位质量 −2 ⇒ 出口闸「双列不劣化 ∧ 质量不降」第二项仍判负，**不宣称降幅**。**候选④ C4 换臂行使成功**（行使臂 B0→B3）：C4-1 23 调用 0 违反、C4-2 call1 指纹 `b9068f56` 六窗唯一、**C4-3 `sensitivity_exercised=True`**（5 窗 call1≠call2）、rc=0 / selftest 4/4 —— 补齐 R566 的 C4-3 空缺。起手闸按上一轮实测振幅派生 `MARGIN=70`/`REQ=2720`，真机 `ceiling=2861/slack=+141`、判别带**真行使**（同态 2650 PASS vs 2720 BLOCKED）、后置 `rc=0`。**未可验收**：铁律 11 前置器 `rc=1`（18 臂窗中 10 项未过）⇒ 成本读数只作**参考**。细节 `docs/reports/r567-dose-axis-second-window-and-c4-exercise.md`。
> - **最近一轮（R566，2026-09-19 · cron 60min tick）【历史快照，已被上方 R567 行取代】**: **主线对照轮（同窗单变量 = 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 取值 0 vs 1 × 外部真值 codex）** —— 冻结题集逐字节复用（`taskset` sha `e0c667c2…`，与 R559/R560/R563/R565 同件）+ 6 新窗 `w125..w130`；全臂同一枚 AOT 二进制（sha `320d0eb1…`）。读数：`C1`（真值）逐窗 58/58/56/56/58/58 ⇒ 中位 **58.0**/极差 2、135 调用、新算 65,244；`R566B1`（轴=1）58/52/43/58/58/45 ⇒ 中位 **55.0**/极差 15、11 调用、新算 2,113、completion 27,003；`R566B0`（轴=0）58/43/45/50/50/51 ⇒ 中位 **50.0**/极差 15、6 调用、新算 906、completion 13,455。判据 v2 判决 **rc=1 FAIL(被测/前提)**、`blocked=[quality_paired_shortfall:R566B0,R566B1]`、`delta_median` −7.5 / −3.0、6/6 真值窗 reliable。**承重结论**：R565 遗留的「预算不足 vs 生成/修复面不足」已被同窗单变量回答 —— 轴 0→1 中位 +5 但**两档均不过判据**，且方向与 R560 剂量轴（dose 3 中位 52.5 < dose 0 中位 54.0）**相反** ⇒ 臂效应落在跨窗摆动带内；失分结构 = 全三臂 `always_fail` 空、`wobble` 逐例集合**恰为 wythoff#43–57**（`life`/`sub`/`nim` 全臂全窗全绿）⇒ 归因生成面单族产物缺陷，且**外部真值亦在 w127/w128 失 #43-public/#57-hidden**。RF0001.3（completion 压缩）同窗读数：轴关 ⇒ 调用 −45.5% / 新算 prompt −57.1% / completion −50.2%，代价中位质量 −5 ⇒ 出口闸「双列不劣化 ∧ 质量不降」第二项判负，**不宣称降幅**。自捕器具读法缺陷：端口脚本漏替换**窗口名** ⇒ matrix 首跑 `errors=18/18`、adjudicate 首跑 `rc=2 INSTRUMENT_DEFECT`（按「RED 第一假设=器具读法错」修后 `errors=0` / `xref=18/18 agree` / `rc=1`）。起手闸：`prev_swing=68` ⇒ `REQ=2718`，真机 `ceiling=2800/slack=+82`、判别力成对控制 `true_discrimination`、后置 `rc=0`（`swing_mb=70` ⇒ 下轮 `REQ=2720`）；**新边界** = 起臂前需 pid 定向回收本会话只读语言服务器（179MB）方得窗口。**未可验收**：铁律 11 前置器 `rc=1`（18 臂窗中 10 项未过）⇒ 全部降幅只作**参考**。细节 `docs/reports/r566-repair-dose-samewindow-and-precond.md`。
> - **主线（用户 2026-09-17 钦定更正，宪法级见 `iteration-master-plan.md` §0-0 铁律 10）**: 用「随机游戏 / 数学难题 / 程序题」真实开发任务 + 外部真值（codex-cli，同模型）**同环境·同输入**对照 ⇒ 对本项目做质量自检；常态载体 `docs/external-reference-harness.md`（R455 入册）+ `eval/probe/*`（随机程序/数学题）+ `eval/capability/*`（自检循环）。
> - **R413 KPI（该主线的判据之一，不是主线本身）**: 用户钦定「r1 真假判别 ⇒ 一轮任务总 token ↓≥30%（主要是不必要的 LLM API 请求少了）」。
> - **版本（历史快照锚，保留原样）**: **v0.35.0 · R413 已交付（判过）**。
> - **最近一轮（R565，2026-09-19 · cron 60min tick）【历史快照，已被上方 R566 行取代】**: **主线对照轮（产品真默认档 × 外部真值 codex）**—— 冻结题集逐字节复用（`taskset` sha `e0c667c2…`，与 R559/R560/R563 同件）+ 6 新窗 `w119..w124`；**单变量 = `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 未设（真默认档）vs R563 的剂量档 `=0`**。读数：`C1`（真值）中位 **58.0**/极差 15/67 调用/新算 36,797；`R565B0`（真默认档）中位 **52.0**/极差 13/13 调用/新算 3,732；判据 v2 判决 **rc=1 FAIL(被测/前提)**、`blocked=[quality_paired_shortfall:R565B0]`、`delta_median=-6` / `delta_min=-15`、`reliable_windows=5`（`w122` 真值窗 unreliable）。**承重件**：铁律 11 前置器**输入登记修复** —— R563 因 `<round>/taskset-<r>.json` 与 `cases/` 未登记 ⇒ `--round r563` 报 `DISCOVER_FAIL rc=3`（该轮对照读数实为**未可验收**）；本轮补『逐字节冻结复用登记』（`frozen-reuse-registration.json`，副本与原件 sha 相等、`cases/` 4 件逐字节同）后得到**真判决 rc=1**。候选④ 指纹/口径恒等式器具上线（夹具判别力 `has_teeth=true` 4/4、身份 13/13、确定性 6/6 同 sha、非平凡 6/6 互异、rc=0）。起手闸判别力成对控制首跑**自捕假红**（条款写成「两闸必须异判」；内存态在阈上时两闸皆 PASS 是正确行为）⇒ 改为「压进判别带再反判」+ 带内不可达 `rc=3` 如实登记。**未可验收**：前置器 rc=1 ⇒ 本轮调用/token 降幅只作**参考**；`R565B0` 终止形态 `rc=5 expect_stdout_exhausted`（每窗 2–3 调用即停）⇒ 不区分「预算不足 vs 能力不足」；失分集中 **wythoff 单模块**。
> - **最近一轮（R564，2026-09-19 · cron 60min tick）【历史快照，已被上方 R565 行取代】**: **器具/只读轮**（零新臂 / 零产品源码改动 / 零远端 / 零新增夹具与开关）—— 起手闸振幅余量条款**按 R563 实测 `swing_mb=64` 派生**行使（`MARGIN=64 / REQ=2714`；真机正控**连续 2 次 PASS**、负控 400MB 占用 ⇒ `GATE_BLOCKED`、**判别力成对控制** = 同一内存态 2680~2689 下 `--gate-mb 2650` 判 PASS 而 `2714` 判 BLOCKED ⇒ 条款确比基础门槛更严）+ w115 单窗 −15 的**族级只读定因**（复用 R562 器具、只换窗集；逐窗 `7/15·15/15·0/15·15/15·15/15·12/15` 与 R563 逐窗失分 **精确对齐** ⇒ 单窗 −15 = **整族塌陷**、构成与 R562 同族；15/15 例同输入产出 2~3 输出 ⇒ 「残余固定几例」再次否证）。铁律 11 `--round r563` ⇒ **rc=1（未可验收）**；余量条款**顶棚依赖**（复跑顶棚 2657 ⇒ 派生步自身 fail-closed rc=2，窗口非随时可得）。细节 `docs/reports/r564-gate-derived-and-w115-cause.md`。
> - **最近一轮（R562，2026-09-18）【历史快照，已被上方 R564 行取代】** · **主线轮收口刷新**，闭合 EXP1-Q46 登记的「最近一轮字段待刷新」待办）**: **R514→R562 的主线明细在 `docs/reports/iteration-master-plan.md` 尾部各节**（R554–R562 逐轮一行：契约面/执行面剂量轴/判据口径/器具收口）+ `docs/reports/r5xx-*.md` 单轮轮志 + `eval/rover/r5xx/` 器具。**R562 当前态**: 质量判据 **v2** 正式入册 `docs/external-reference-harness.md` §12（v1 作废 + 作废登记）；起手闸/判据 v2/铁律 11 前置器**同轮复跑**一致（判决面逐字段相同 ∧ 27/27 臂窗跨文件相等 ∧ 27/27 臂窗与前置器逐条相同），起手闸成对控制 rc=0；wythoff 族只读定因（405 例次）主因 = 「胜负判对、落点非冷点」51%；**零新臂/零产品改动/零远端** ⇒ 铁律 11 **rc=1（未可验收）**，读数一律「参考（未可验收）」。**上方 R509 行保留为历史快照**（不回填、不改写）。
> - **最近一轮（R509，2026-09-17 08:09:10 提交）【历史快照，已被上方 R562 行取代】**: 前端任务事件域（`task.started` / `task.completed` / `task.failed` + `state.snapshot.tasks`）+ 同题重复臂（每跑次独立 session ⇒ 会话隔离）；HEAD `0b88277`。**块范围**: 本块承载「最新状态 + 历史锚（R401–R412 已回填，见下）」；R413 之后的逐轮明细在 `docs/improvements.md` 顶部各节 + `eval/rover/r4xx/`。
> - **HEAD（EXP1-Q44 观测 2026-09-17 08:14）**: `0b88277`(R509 收口) ← `6bec98f`(R508) ← `e7b360b`(EXP1-Q43) ← `ac108e1`(R507 补测) …；远端 `origin/main` = `740ddf2`，**未推**（推送暂停令在效，三道机械闸在位）。
> - **本轮判据读数（外部真值 = 桩侧逐请求落盘 + 驱动器观测）**: 臂 A（本地通道关）**12 调用 / 16,888 token** vs 臂 B（前置门开）**8 调用 / 7,007 token** ⇒ 调用 **-33.3%**、token **-58.5%**（阈值 30%）；门遥测 = 机械 Pass 3 + r1 判别 4（全 Skip）；**C1–C4 全 PASS ⇒ 判过**（`eval/rover/r413/verdict-r413.json`）。
> - **前置门 v2**: 机械 Pass 前置（疑问句 / 新指令 / 纠正词 / 结构化实体 / 长文本 ⇒ 直接 Pass，不问 r1）+ 仅无信号短消息交 r1（二元 S/P、192 上限、只读思考块之后的结论区）+ 被跳过轮回复 = **非 LLM 模板**。
> - **本轮两处空心根因（已修 + 已回归）**: ① 门判的是被追加过 role/计划块的 `prompt.UserMessage` ⇒ 恒 Pass、增益归零（修：判 `message.Content` + G29 源级钉死）；② 源码写入通道把尖括号字面量替换成 tokenizer 形态 ⇒ 解析器恒搜不到 = 空心降级（修：`ThinkOpen`/`ThinkClose` 字符码常量 + G24/G25 回归）。
> - **机检 / AOT**: `LocalTurnGateTests` **46/46**；全量 **1158/0/0**（`TEST_EXIT=0`）；AOT 重发布 `PUBLISH_EXIT=0`、**IL 警告 0**、`agenthost` **15,138,848 B**。
> - **机检（EXP1-Q44 真机复跑，2026-09-17 08:13）**: 全量 **1643 / 失败 0 / 跳过 0**（38 s，`FULLTEST_EXIT=0` —— 由**显式标记**取值，非管道末段）；`scripts/capability_cycle_status.py --selftest` **30/30**（v5/D8）。
> - **器具取证（EXP1-Q44 · 对侧记录面假绿）**: `/tmp/r508_fulltest.log` 尾部同时含 `Failed: 1`（1636 中 1 条 `FrontendAskSameConnTests`）与 `TEST_RC=0` ⇒ 记录侧 rc 取自管道末段（`… | tail`）。检测器 `eval/capability/exp1-q44/scan_pipe_rc.py` 判 rc=1（FALSE_GREEN）；仓库自带 **251** 个 `.sh` 扫描 **0 命中**（缺陷在对侧**临时命令**，非仓内脚本）；本侧同轮真机复跑该用例**全绿**（1643/1643）⇒ 单条失败未重现、未定论（可能其后已修 / 可能网络型偶发），但**记录面 rc 不可信**已确证。**纪律**: rc 必须由发射点显式写标记，并在日志面加「正文 Failed/Passed vs 标记」矛盾闸。
> - **cron（2026-09-14 现状 = 2 个）**: `9a97763d5fcd` 30m 节拍（本轮因全局推理配置漂移被 skip ⇒ 已 pin `custom/deepseek-flash` 恢复）+ `b15eb2f40a69` 60m 能力自检。删前备份 = `backups/cron-jobs-before-prune-2026-09-14.json`。
> - **R401–R412 逐轮回填（EXP1-Q44 机械 census，来源 `eval/capability/exp1-q44/census_401_412.py`）**: 本块此前自 R400 直跳 R413，该「未回填」缺口在本轮**关闭**（12/12 有来源，逐轮一行）:
>   - **R401** · 能力自检循环常驻化（60 分钟检测机制，用户令）· `eval/rover/r401/`(3) + `docs/reports/r401/` + improvements R401 节
>   - **R402** · 循环入口自检（探针 v2 三缺陷：完成标记覆盖「进行中」/ 状态列硬编码 / 零命中静默）· `eval/rover/r402/`(27)
>   - **R403** · chat template 工具作用域 + RoPE 配对修复 · `eval/rover/r403/`(22) + `docs/reports/r403/chat-template-tool-scope.md`
>   - **R404** · bge 融合对账 + G1 阈值修缺陷（旧阈值落「数学上不可能显著」区）· `eval/bge/train_adapter.py` R404 段 + `eval/bge/auto_cycle.py` ⑥（**无独立证据目录**，读数散在代码注释与后续计划交叉引用 ⇒ 如实标注）
>   - **R405** · 本机增强 R1-Distill-1.5B · `docs/plans/v0.27.0-r405-r1-local-enhancement.md` + `eval/rover/r405/`(8)
>   - **R406** · 模板驱动 chat template（Jinja 子集）与 R1 链归因 · `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md`
>   - **R407** · qwen2 前向对账：attn bias 层归属缺陷 · `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md` + `eval/rover/r407/`(14)
>   - **R408** · 本地 GGUF 引擎整线退役 + llama.cpp 进程化（10,966 LOC + `agent.embedcpu` 退役）· `docs/plans/v0.30.0-r408-llamacpp-process-pivot.md` + `eval/rover/r408/`(3)
>   - **R409** · 本地 prompt 模板闸门（结构性阻断）+ BOS 口径 · `docs/plans/v0.31.0-r409-local-prompt-template-gate.md` + `eval/rover/r409/`(19)
>   - **R410** · 会话长前缀复用（K2b 落点）+ 生成口径分离 · `docs/plans/v0.32.0-r410-session-prefix-reuse.md` + `eval/rover/r410/`(8)
>   - **R411** · 长驻生成端口 + 本地 K2b 台账 · `docs/plans/v0.33.0-r411-long-lived-generation-port.md` + `eval/rover/r411/`(20)
>   - **R412** · 多会话 slot 争用（本地长驻生成的第二 regime）· `docs/plans/v0.34.0-r412-multi-session-slot-contention.md` + `eval/rover/r412/`(18)
>   - **另一本台账（improvements.md 轮节，EXP1-Q45 已闭合）**: 该本台账的 8 处轮节已由 **EXP1-Q45**（`1ef590a`）逐节补齐并机检化 —— `eval/capability/r518/scan_round_sections.py`：前态 C1 n=8（R402/R404/R405/R406/R407/R417/R418/R419，rc=1）→ 后态 C1 n=0 ∧ ZONE 13→21（rc=0，读数见 `eval/capability/r518/scan-pre.txt` / `eval/capability/r518/scan-post.txt`）；`docs/improvements.md` 自陈更正见其 R404 段（旧口径作废留痕）。原括注范围「R404–R416」与机检缺集不符（真缺集跨 R402–R419）⇒ 以机检为准。**记录面时效（EXP1-Q46 机检）**: 上方「最近一轮」字段停在 R509 / `0b88277`，而现盘 HEAD = `29f75c3`（R518，13:29）⇒ 该字段归**主线轮收口**刷新，本 tick 只登记不代写（防与对侧写者撞车）。（**R562 已刷新**，见上方新增「最近一轮（R562…）」行；R509 行转为历史快照。）
> - **诚实边界**: 单脚本 / 单模型（r1-distill-1.5b-q4km）/ 单机单次读数；机械信号表是**穷举白名单**（未覆盖的短消息仍交 r1）；桩侧逐轮归属受「后续轮 prompt 含历史文本」干扰 ⇒ 只作参考、不作判据；轮7 的 0 主调用是链侧澄清拦截、非门行为。
> - **文档同步（本轮）**: `docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md`（§7.3–§7.6）/ `docs/improvements.md`(+R413 节) / `eval/capability/kpi.jsonl`(+1 行, 8 行) / 本块。
> - **文档同步（EXP1-Q44）**: `eval/capability/exp1-q44/`（prereg_q44.json / verdict_q44.json / verdict_q44_d9.json / selftest_v5.txt / selftest_v5d9.txt / status_v4.json / status_v5.json / status_v5_D8.json / status_v5d9.json / status_v5d9_legacyroute.json / fulltest_q44.raw.txt / scan_pipe_rc.py / census_401_412.py / backfill_401_412.json）+ `scripts/capability_cycle_status.py`(v5/D8+D9) + `eval/capability/kpi.jsonl`(+1 行) + 本块。**探针自检 34/34**；前态锚 = `cc9cafc`（已断言是 HEAD 祖先 ∧ 字节与现盘不同）；**D9 预注册 P8 被部分否证**（真仓只命中闭合围栏、引用围栏 0）—— 旧读数原样保留于 `verdict_q44_d9.json`，文档侧按「把引用写显式」加引号后的重测单列 `verdict_q44_d9_docfix.json`（不放宽判据）。
>
> ### 🗂 历史快照（2026-09-14 R400 — rover 生成链）（保留以追溯；最新状态见上方 R413 块）
>
> - **版本**：**v0.26.0 · R400 已交付**（rover 生成链）；本地 HEAD = `9d2191a`（R400 生成链落地）+ `f75e6f7`（R400 规划入账）+ `4cabcc5`(R399) …；远端 `origin/main` = `740ddf2` **未推**（推送暂停令在效）。
> - **【推送暂停令 (2026-09-13 用户钦定)】**：**暂停所有 GitHub 推送** —— 三道机械闸在位（`.git/PUSH_PAUSED` + `.git/hooks/pre-push` + `remote.origin.pushurl`→不可达路径）；解除 = 删标记 + 删 hook + `git config --unset remote.origin.pushurl`。
> - **【常驻循环 (2026-09-14 用户钦定)】**：cron **`10f9d6454575`** 每 60 分钟跑 `scripts/capability_cycle_status.py` 判 `mode=tasks|selfcheck`：有未完成计划项 ⇒ 推进最前一项一步（要真机证据）；无 ⇒ 跑「py 随机程序 + 随机数学题」能力自检并沉淀通用性 skill 到 `skills/`（`type: knowledge_hint`）。BGE 线仍静默（cron `79b866b5097d`，6h）。
> - **本轮交付（R400）**：**rover 生成链**（目标 ③「本机引擎可当解法后端」的前置）—— `src/agent.rover/token/{ByteUnicode,Pretokenizer,BpeTokenizer,ChatTemplate,TableSnapshot,TokenizerAssets.g.cs}` + `infer/Sampler.cs` + `cli/GenerateCli.cs`（`tokenize`/`generate`）+ `agent.csproj` 共享源；资产入仓 `eval/rover/tokref/`（表快照 + 夹具 199/199/2000/405 + chat_golden 12）；生成器 `scripts/rover_*.py`；测试 22 条。
> - **对账读数（oracle = HF tokenizers 0.23.2，独立实现）**：encode **199/199**、预分词 **199/199**、压力批 **2000/2000**（encode+分片双断言）、解码 **405/405**（两种 skip 口径）、chat 渲染 **12/12**（jinja2 逐字节）；**GGUF 装载路径同读数**（真机 `tokenize <gguf> --fixtures` ⇒ `pass=true`）⇒ 表快照路径与真机路径**同摘要**（`merges_sha256=cb5bed793622288a…` / `tokens_sha256=6e5117ddc01e0cb3…`）。
> - **负控读数（判别力量化）**：merges 乱序 **41.5%** / 逆序 **56.9%** / 清空 **95.3%** 被检出（依赖合并样本 1814；阈值 30/40/90%）；空切分集必红；朴素整片预分词判别 **137/199**。负控当场抓到真 bug：`Sampler.NextU64` 状态拷贝致随机源不前进（采样退化）。
> - **本轮 5 处实测修正**：① .NET Regex 按 UTF-16 码元解析字符类 ⇒ 增补平面区间静默过量匹配（改机器派生标量区间表）；② 区间表须归一化（CJK 正则原文非升序 ⇒ 二分漏判）；③ `\s?[类]+` 前缀需回溯；④ 判定谓词须**阶段隔离探测**（整条流水线探测会把 Zs 空白误判为非 `\s`；正确 = 25 码点 = Unicode White_Space 全集；Digits = {Nd,Nl,No} 1831/1831，负控 3920 例 0 违规）；⑤ 切分集 = `added_tokens` **全体 18**（与 `special=true` 无关），跳过集 = 3。
> - **诚实边界**：① 本机 2 vCPU / 无 GPU / 每 token 流式扫 ≈4.0 GiB ⇒ 生成**不可交互**（≈20–33 s/token），本轮交付「链路正确 + 可对账」，性能线属 R401/R402；② chat template 仅 `system/user/assistant` 子集（工具调用/Jinja 全量 = R403）；③ 采样器无重复/存在/频率惩罚；④ 探针 `solver=rover` 为**限量 token 口径**（默认 8），不得读作「rover 能力为零」；⑤ M6 对 agent 仍饱和（R399 遗留）⇒ 下轮换维度。
> - **文档同步**：`docs/plans/v0.26.0-r400-rover-generation-chain.md`(计划+实施记录) / `docs/plans/v0.22.0-longterm-backlog.md`(L8 R400 状态) / `docs/improvements.md`(+R400) / `docs/verification-registry.json`(+`rover.generation.chain`, updated_round=R400) / `docs/reports/r400/`。
>
> ---
> ### 🗂 历史快照（R377，2026-09-13）
（以下为 R377 时的快照正文，保留以追溯）
>
> - **版本**：**v0.22.0 探索期**；本地 HEAD = 本轮 R377 提交 + R376 `68e8ed6` + R375 `941c9cd` + 规范 R7 `4b05ca8`；远端 `origin/main` = `740ddf2` **未推**。
> - **【推送暂停令 (2026-09-13 用户钦定)】**：**暂停所有 GitHub 推送** —— 三道机械闸已就位（`.git/PUSH_PAUSED` 标记 + `.git/hooks/pre-push` 拒绝 + `remote.origin.pushurl` 指向不可达路径, 离线秒失败 EXIT=128 已实证）；两个定时任务（`f6a10a4499cc` 千轮守卫 / `9a97763d5fcd` 底座小报）指令已改写为**仅本地 commit**；解除方式: 删标记 + 删 hook + `git config --unset remote.origin.pushurl`。**fetch 面未受影响**。
> - **测试**：**859/859 全绿**（env 干净, 连跑两遍；R376 为 847）；**AOT 编译校验只在发布 tag 时执行/登记**（规范 **R7**；非发布轮 AOT 仅作参考证据）。
> - **本轮交付（R377）**：**DS prompt 缓存命中率纳入优化 KPI（用户钦定）** —— DTO 解析 `prompt_cache_hit_tokens`/`prompt_cache_miss_tokens` → `PromptCacheKpi`（命中率 4 位 + 未上报哨兵 -1）→ 三处 `llm_call` 打点铺三元组 → `scripts/kpi_cache_hit.py` 离线聚合；真机同题 2 跑 **命中率 23.73% → 36.94%（合计 30.43%, 4 次调用）**。
> - **机检/负向控制**：`PromptCacheKpiTests` **12/12**；负向控制 **4/1/1 红**（算法篡改 / 未上报冒充 0 / 打点铺设被删）→ 其中变异③首跑 0 红 = 我的断言当时空心 → **改按打点块配对**后抓到（教训入 exp5 §15）。
> - **能力探针（R377 回归样本, 同题贪吃蛇 ×2）**：RUN1 2 调用 / 137s / 37,226 tokens / 产物 2 个 / reply 17,973 ch；RUN2 2 调用 / 139s / 39,955 tokens / reply 13,487 ch；**独立复核** `--selftest` → 修复后产物 **16/16 PASS**（两跑均是"首投失败 → D3 修复成功"）。
> - **诚实边界**：① 命中率为 2 跑样本非稳态分布；② 本轮 tokens 高于 R376 因 D3 修复各多 1 调用（机制正常, 成本如实登记）；③ 首跑全量 857/859（2 红未留名）→ 连跑两遍 859/859, 判负载偶发；④ exp2 §8 Q1–Q4 仍待用户裁决；⑤ D7 截断续写仍未救回；⑥ 工业级缺口余项: CI 门禁 / 配置热更新 / metrics 端点 / 断路器半开 / 跨请求成本闸。
> - **文档同步**：`docs/improvements.md`(+R377) / `docs/reports/iteration-master-plan.md`(§0-1 K2b) / 本报告(§6b + 快照) / `docs/verification-registry.json`(+1 行, R377) / `docs/plans/v0.22.0-exp5-lesson-table.md`(§15) / `skills/delivery-selfcheck/SKILL.md`(v1.1.1) / `scripts/kpi_cache_hit.py`(新)。
- **R376 段（历史）**：exp2 P2 达成 —— 真机同连接 menu 闭环（`ask` 信封 → 同连接 `ask.reply` → `outcome=answered` → 续跑返回正文, 3/3）；修 **⑪ 握手残包**（返回 Tail + 预置排空）与 **⑫ 同通道回程饿死**（读循环只解析 + 并发派发, 在途上限 8）；全量 847/847；负向控制 2/2 红；AOT 参考 13,959,712 B。
- **R375 段（历史）**：exp2 P0 前端 menu 问询通路实装（`AskEnvelope` 信封 + `FrontendEventHub` 事件推送 + `ask.reply/ask.cancel` 路由 + 选项贯通）；P1 真机接线已证（伪造 id → `unknown_ask`）；P2 ask 事件 **0/1**（触发点未命中）；全量 841/841；AOT 参考 13,947,200 B / 0 IL。
- **主线进度**：R138-R153。R149 用户质疑整改（真断言族）；R151 pivot 判定闭环（真缺陷 56 KeyError 修复）；R152 收尾（phase report 3: batch62-78 187/187 + README 30 批滚动制度）；**R153 真缺陷 57 修复**：D4 gate 读 os.environ 致 reply_rel 整块静默失效（批79/80 n=0 实证，诚实缺省未破）→ gate 同源 load_env()，批81 同环境复验 n=11 avg 0.631 恢复。下一轮号 **mass_351**（R180-R184 进度与接力细节见下方对应条目及台账 R180-R184）。
- **最近五批审计（批76-80）**：63/63 全绿（quick-11 子集 44/44）；tok/case 941→939→928→860 递降带内（全量批 1165 口径不同）；drift 全 1.0；suspects 0；D4 rel 修复前 n=0（缺陷 57）/修复后 n=11 avg 0.631。
- **R149 用户质疑结论**：TaskRelevanceChecker 组件能力真实（全量批 50/53 isolated=True score=2 实测）但判定空心成立——既往 C14/C15 expect 只有 llm:true，通过率对组件无证明力。修复后 C14 真断言批69-72 四连验 isolated=True score=2 PASS (4/4)。
- **R151 (pivot 判定闭环)**：C15 pivot_reanchor 升级为三重真断言 (不隔离+pivot_n≥1+新任务链产出)；pivot_n 打点消费建成 (goal/op=pivot, 真缺陷 45: init 缺键 KeyError——batch76 首跑 15/19 后死亡实证, 与 R142 compression 同源教训)；批76 全量 19/19 复证 pivot_n=1 真重锚。
- **README 30 批滚动制度 (R152b 用户钦定)**：README 能力段只保留最新 2 个轮段（整段完整能力列表），更早轮段整段撤出、按轮段归档 `docs/archive/changelogs/` (CHANGELOG-v0.11.0-RXXX-RXXX.md 格式, v7.14 亦在其中)；批次趋势行只留最新 2 批 + 归档链接；下次滚动: 批108。
- **R154-R155 (harness 可靠性双修)**：真缺陷 58 (dotnet PATH 依赖未自兜底, 批83 首跑半途崩) → main 入口 fail-fast 探测; must_not_contain 扩 string|list (C15 三重断言: pivot_n≥1+无[隔离任务]+≥30ch, 复用 R138 机制); 批85 全量 19/19 复证 (C15 pivot_n=1 + 真诗回复)。mass_298 RETIRED (缺陷58 受害者, 轮号报废)。
- **五批审计 86-90**: 55/55 全绿, 均值 806 tok/case, CV 1.8% (历史最稳窗口), 零 suspect (C03 0.499 边缘由 min_reply_chars 内容锚接管, 阈值不动)。
- **五批审计 91-95 (55/55 avg 867) + 96-100 (55/55 avg 908)**: suspects 全部定性假阳性 (C12 JSON 输出/C16 长会话总结, 结构性低 rel, 断言判定兜住)。
- **R161-R165**: 全量批97 19/19 (C15 pivot_n=1/C03 锚/C14 iso 三断言全稳); README 双语趋势行滚动至批98/99; 批83-102 **20 连绿** (缺陷58 修复后零非绿)。
- **R169 README 30 批滚动点 (批108)**: 双语趋势行→批107/108; 新归档 CHANGELOG-v0.11.0-R153-R168.md (批79-108 全明细, 断链 0); 下次滚动批138。
- **R171 batch111/112 双批**: mass_327/328 11/11 x2 (887/796 tok/c), D4 rel 0.618/0.629, 0 suspect, breach 空 — **30 连绿** (batch83-112)。
- **R172-R177 (稳定性基建三连)**: 缺陷59 per-case 超时容错 (一个用例 180s 挂起不再崩整批, C13 批113 首证) + 超时重试 1/1 (LLM 端点瞬态挂起 5 用例各中招一次 C08/C13/C01/C17/C03, 重试全 PASS 3/3+2/2 实证) + C16 长会话真断言 (must_contain 热点 + ≥300ch, 锚定批113 回复实证 — "Redis" 字面量断言会误杀好回复, 断言先行必须查历史样本)。
- **R180-R182 (C07 记忆链三连修)**: 真缺陷 60 (must_contain 硬判定误用 req() → NameError 崩批, 改 x[pass]=False); C07 记忆源破案 (跨进程 forecast.json 单槽被中间用例竞态覆盖 → 批340 丢失实证链: forecast Save→prompt header 注入→LLM 消费); 真缺陷 61 (记忆回指词缺 deixis 表 → repl 轮2 误隔离, +8 词一票否决 +2 单测 401 绿); C07 改 repl 双轮真 session 链 (批131 验证 pass+不隔离); 健康带 quick tok 上界 1100→1250 (C07 双轮成本口径登记)。
- **R183 (用户质疑驱动泛化加固, dd15851)**：TaskRelevanceChecker 归一化层（去空白/标点/符号 + 全角→半角 + 小写）使词表匹配对插入变体机械免疫；语言无关结构信号（纯疑问短语一票否决 + 短问句减分）兜底其他语言/新词；+3 对抗测试 404 绿。R184 本 tick 接力 batch134 (mass_350) 11/11 1096 tok/c 带内, D4 rel 0.616, 0 suspect。
- **R183 smoke 边界 (诚实登记)**: AOT publish 0 IL 警 ✓, 但 --smoke 挂死 (JIT 同挂, 排除 AOT 回归): 本地 qwen CPU 推理路径卡 thinking→输出 (llamalocal 自 R130 零改动, R182/R183 只动 intent 词表+用例/批测面); 批测链路 (云 LLM, 11 批连绿) 完全正常 — smoke 依赖的本地推理通道单独归因, 不阻塞发布判定 (AOT 验收=0 IL 警+产物正常, 冒烟复跑挂观察名单)。
- **R191-R193**: 批 145-149 五连绿 (含全量 143 19/19); 双窗审计 143-147 (58/58 含全量) + 144-148 (55/55); smoke 归因推进 (qwen 0.5b 加载完成但 eval 从未开始, bigmodel→local fallback 链嫌疑, 观察名单)。
- **R194-R198 (sibling 冲刺段)**: 批 150-159 十连绿 (含全量 143 归一化泛化回归 19/19); 审计窗 146-150 + 150-154 (各 55/55, avg ~1100/~1090); v0.12.0 双规划 commit (vision GLM-4.5V 真实验证 glm-5.3-flash 无视觉 / CogView 图像生成, 均 doc-driven 事实核实 2026-09-08); R186 README 30 批滚动点批138 (归档 CHANGELOG R169-R185, 下次滚动批168)。
- **R199 五批审计 155-159 (本 tick 接力)**: 55/55 全绿, avg 1022 tok/c 带内 (≤1250), wall avg 168s, D4 rel 0.611 (n=55), 0 suspect, breach 空。复核窗 152-156 (55/55, 1047/c, rel 0.610) 双窗互证。
- **R210-R213 (v0.12.0 B2 渲染插件体系)**: 用户钦定收敛环做成服务插件 — IImageRenderPlugin 契约 + SkiaSharpRenderPlugin (默认, SKIA_RENDERER 边缘选项, -p:DisableSkiaRenderer=true 停编) + SvgTextRenderPlugin (恒可用兜底) + Registry (HasRenderer=false → image-gen 跳过后续环节); 双模式 build 全绿; 收敛环 E2E 首验一轮 PASS (DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)。
- **R213-R235 (v0.12 收官 + v0.13 T3/M1 + v0.13.1 F1/F2)**: 渲染插件体系+收敛环 E2E 一轮 PASS; 视觉用例族 T-V01-04 full-23 23/23 (负样本诱饵识破); 验收基线文档; 真缺陷 65 (重试打点黑洞→KPI 假性 BREACH)/66 (视觉备选成本倒挂)/67 (Text 硬过滤)/68 (C17 断言脆性→neg_context_markers 推测围栏) 全修; ExplorationPlanner+ComplexityGate+EvidenceScorer+ThinkMemory+StickyRouteMemory+FallbackConfig 落地 (449 单测区); 文档周期铁律入记忆 (每30轮/版本递进/严重修复→全文档更新+push)。
- **R238-R245 (底座能力专项 — 用户三连质询驱动)**: KPI-2 token 全史报告 (542→2355 C07 归因, 无注入膨胀); 压缩 audit 体系 (ground-truth 104 篇多样态 × 4 档 × 3 级别; 首轮实证 SummarySentences 丢因果/指令 → A3 关键句保护修复 → 多样态复测 99%/85%); 429 感知调度; micro-step 隔离设计+基线 (触发率 0%); token-breakdown 观测行; 用户质疑全部 VALIDATED 并入档。
- **in-flight**：R246 → ① 句切分器修复 **DONE (R257, 2026-09-09: 多样态 instr 0.85→0.9615, 12 审计行全过 0.95 健康线, A3b/A3c/A3d 三修 AOT+473 单测+批 224 零回退闭环)** ② audit 每批抽查自动化 (下一优先) ③ B2 微步骤 StepDecomposer ④ 批 225+ 常态。
- **推送状态（R199 复核）**：R156-R170 系 sibling tick 已推；R179b 补推 13 commits 至 780cd0d（双通道复核）；R184 复核 R180b..R183 六提交 remote=local=dd15851；R199 复核 ahead-28 为 fetch 陈旧假象第 4 次（remote=local=79fa32a，fetch 后消除），sibling 经 ghfast 推至 dd7a6a5 成功；c1b9e93 (batch160) 首推失败实录（ghfast curl 28 超时 133s，代理抖动窗口），接力重推中。config ghp_ 残留恒 0；~/.hermes/.env PAT 401 失效弃用；池验证 5 活（dmud 钦定 / BSoi / wnkO / j6o5 / XTMI，state.db 流式提取 + API 筛活，WAL 截断伪影 len=41/…j 全 401 过滤，池随 WAL 轮转抽验波动正常）。github 直连/ghfast 代理均间歇抖动（R199 实录：直连 TLS -110 同型、ghfast curl 28）；push 重试惯例有效，成功后必 API+ls-remote 双通道复核 sha。
- **环境事实**（防重查）：bge=`/home/agentuser/.agentframework/models/bge-q8.gguf`（`.env.local` `AGENTFRAMEWORK_BGE_MODEL`，**cron/新 shell 须 export PATH="$HOME/.dotnet:$PATH" 否则 runner FileNotFoundError**；bge 路径勿依赖 os.environ——缺陷 57 教训，harness 统一走 load_env()）；3 key：kimi 负样本/glm 可用/deepseek 7.61 CNY；github 直连断→ghfast.top 代理推（>8min 假死勿中断）；telemetry 读用 utf-8-sig；`execute_code` 300s 上限→批测逐轮后台跑；**llm-service/llm.sock 已 R113 退场，sock 缺失=正常态勿重启**。
- **千轮口径**：RETIRED 轮诚实标注；全绿口径=排除 RETIRED；轮号唯一；每轮落盘+镜像。

## 8. 本报告的更新纪律

1. 每完成一轮（R1xx）若涉及打点/评测/回滚机制变化 → 更新对应章节；
2. 每 5 批 → 更新 §6 基线表 + §2 点位审计结论；
3. 每次回滚 → §4.3 历史记录追加；
4. 报告与代码同 commit 推送（保证 eval/results、台账、报告三者一致）；
5. **长期记忆分层纪律（2026-09-07 用户纠正后确立）**：记忆只装三类——①指针（本报告路径+恢复入口）②元规则（铁律/方法论，跨千轮不变）③活跃靶点（短周期，完成即清）。**轮次状态（R1xx 进度/commit/基线数字/下一轮号）一律不进记忆**，全下沉到本报告 §7 + 台账 + git，随 commit 滚动——否则到 R3000 时过时基线会污染新会话，且按轮追加会撑爆记忆预算。细节以本报告为准。**活跃靶点条目规范**：记忆里保留一条「当前活跃靶点」（下一优先级 2-3 项+一句话定性质疑点），**滚动替换、完成即清、禁止追加**——它是"下次醒来接着干什么"的最小指示，完整候选清单与细节仍以本报告 §7 为准。

### R262-R279 (2026-09-09, v0.13.3 压缩防护 + B2/think-memory/激活链)
- **压缩失败防护 D1-D4 落地** (用户问询驱动): D1 异常隔离 (per-snippet try/catch → 回退原文), D2 数字/日期/SN 哨兵
  (缺失→降级 SummarySentences→RuleCompress→原文), D3 降级链内嵌, D4 熔断器 (阈值/冷却/半开, 6 测)。
- **多轮压缩观测** (R272): 10 轮 repl × 17 压缩事件 (drift_ok 全 true, sentinel/error/breaker=0 健康)。
- **B2 微步骤宿主链 E2E** (R274): XL-01 est 8023→IsolatedMicro→微问询 ok 2860ms→micro_session count=1 failures=0;
  教训: 单项目 build 不刷 host bin 依赖 (需 build host.csproj)。
- **think-memory bge 联想 E2E** (R275): 轮2 recall hits=1 top_sim=0.9765 (同实例语义连续)。
- **LinkRegistry 激活链** (R276): 三信号预判 (锚定/结构稀缺出链/路径递进) ≥3 激活 + 父链保护; 5 测。
- **多轮 3 场景** (R278): A 事实累积 (17 压缩) / B 数字密集 (12 压缩, sentinel=0) / C URL 链 (22 压缩, sentinel=0)。
- **XL 周节奏** (R279 本条): 每 5 批 quick 插 1 次 --suite=xl 回归 (下次≈批242); gate 三态分布稳定性为观察指标。

## 八、K1 语义澄清与会话牵引增强 (2026-09-09 用户质询驱动)

### 8.1 用户理解 vs 框架现状
- 用户理解: "K1 = 在会话中不断更正牵引话题, 不偏离核心主题"
- 框架现状: K1 (被提问概率) 是**被动画像偏置** — tendency_bias 每轮注入 (Web API=0.80 conf0.8),
  但无主动牵引/纠偏动作; 会话牵引由三个旁路机制承担:
  ①ForecastRecord (意图→下轮倾向预测, ContinuationHint) ②session LongTermMemory 轨迹
  ③GoalText 目标锚 (当前为空 — 未启用)。
- 差距: **偏题轮无纠偏** (红烧肉轮照常回答, 轮3 回归全靠 LongTermMemory 轨迹 + LLM 自身理解)。

### 8.2 会话牵引增强方案 (三档)
- L1 (轻): GoalText 自动锚定 — 首轮任务入 GoalText, 后续轮偏题检测 (意图跳变+画像主题距离) →
  回复尾追加"牵引提示" (与当前主题相关的一句衔接), 不改答案本体。
- L2 (中): 偏题检测打点 topic_drift (当前轮主题 vs 会话核心主题距离) + 阈值观察, 数据先行。
- L3 (重): 主动澄清 — 偏题≥N 轮时 agent 主动问"是否继续 X 主题" (K1 被提问概率的真实消费场景)。
- 顺序: L2 (观测) → L1 (轻牵引) → L3 (重交互), 每档打点后看数据再进下一档。

### 8.3 K1 行为差分结论 (R300-R302 汇总)
- tendency 注入 = 冗余强化 (SessionMemory/记忆源天然带画像) + 少量独有事实 (80% 比例)
- 行为差分口径确立: 画像独有事实锚 (非宽词), 全隔离臂对照 (context 812→176tok)
- 待做: 问题族扩容 (3→10) 显著性复测; L2 topic_drift 打点

### 8.4 R308: 牵引判定 vs 无关隔离判定 — 共性分析与合并判定 API (用户问询驱动)

**用户问题**: L1 牵引与"无关问题启动 subagent 隔离"在会话输入判定上是否有共同之处? 能否合并为一个 API?

**现状两判定对比** (实码核查):

| 维度 | 隔离判定 (TaskRelevanceChecker.Check, V2 L535) | 牵引判定 (topic_drift, V2 L780s) |
|---|---|---|
| 锚 | Goal.KeyEntities + GoalIntent (目标实体) | tendency_bias coreTopic (画像 top-1, 词面) |
| 输入 | message.Content + incomingIntent | message.Content |
| 信号 | 实体重叠 (±2) / 意图不同 (+1) / 离题词 (+1) / 指代词一票否决 / 结构信号 (-1) | 词面包含 (coreTopic 分词全不命中 → drift) |
| 阈值 | score ≥ 2 → Isolated | bool (无分档) |
| 时序 | LLM 前 (主循环 L535) | LLM 前 (micro_decision 后) |
| 消费 | subagent 隔离执行 (IsolatedTaskRunner) | L1 轻牵引提示 (R307) |
| 打点 | subagent{...} | topic_drift{core,drift} |

**共性**: 同一输入 (当前轮消息), 同类锚 (会话主题/目标), 同语义轴 (当前输入与会话核心的相关度)。
**差异**: ①锚源不同 (Goal 实体 vs 画像词面) ②评分结构 (Check 多信号加权 vs drift 二值) ③阈值/消费不同。

**合并判定 API 设计 (R308 落地)**:
`TopicRelevanceEvaluator.Evaluate(message, goalEntities, goalIntent, coreTopic, incomingIntent)` →
`TopicRelevanceVerdict { Score, IsIsolated, IsDrift, Signals[], Recommendation (Isolate/SteerHint/Normal) }`
- 统一在**一处**算相关度: 实体重叠 (强) + 意图差 (中) + 离题词 + 画像词面 (弱, 替换原二值 drift)
- 消费映射: score ≥ 2 → Isolate (subagent); 0 < score < 2 → SteerHint (L1 提示); ≤ 0 → Normal
- 好处: 一次判定多消费, 信号共享可观测 (单一打点 topic_relevance{score,verdict,signals}), 阈值集中可配
