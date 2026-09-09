# 动态打点测试评测回滚策略说明报告

> **文档性质**：AgentFramework 千轮迭代主控报告（随千轮任务持续更新，最新版本随每次提交推送 GitHub）。
> **主题（用户钦定 2026-09-07）**：针对用户话题倾向，围绕用户体验，使用动态打点策略，不断优化迭代 agent 功能。
> **恢复迭代入口**：上下文丢失后，读本报告 §7（迭代状态快照）+ `eval/results/mass_*.json`（自动镜像轮数据）即可继续，无需其他上下文。
> 最后更新：R308（2026-09-09）· commit 见 `git log --oneline -1`
> **方法论总纲**：何时新增点位/如何探索点位/测试数据源设计（含负面数据）/跑测真实性校验 → 见 **`docs/reports/iteration-master-plan.md`**（方法以它为准，状态以本报告为准）。

---

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

## 7. 迭代状态快照（恢复迭代从这里开始）

- **主线进度**：R138-R153。R149 用户质疑整改（真断言族）；R151 pivot 判定闭环（真缺陷 56 KeyError 修复）；R152 收尾（phase report 3: batch62-78 187/187 + README 30 批滚动制度）；**R153 真缺陷 57 修复**：D4 gate 读 os.environ 致 reply_rel 整块静默失效（批79/80 n=0 实证，诚实缺省未破）→ gate 同源 load_env()，批81 同环境复验 n=11 avg 0.631 恢复。下一轮号 **mass_351**（R180-R184 进度与接力细节见下方对应条目及台账 R180-R184）。
- **最近五批审计（批76-80）**：63/63 全绿（quick-11 子集 44/44）；tok/case 941→939→928→860 递降带内（全量批 1165 口径不同）；drift 全 1.0；suspects 0；D4 rel 修复前 n=0（缺陷 57）/修复后 n=11 avg 0.631。
- **R149 用户质疑结论**：TaskRelevanceChecker 组件能力真实（全量批 50/53 isolated=True score=2 实测）但判定空心成立——既往 C14/C15 expect 只有 llm:true，通过率对组件无证明力。修复后 C14 真断言批69-72 四连验 isolated=True score=2 PASS (4/4)。
- **R151 (pivot 判定闭环)**：C15 pivot_reanchor 升级为三重真断言 (不隔离+pivot_n≥1+新任务链产出)；pivot_n 打点消费建成 (goal/op=pivot, 真缺陷 45: init 缺键 KeyError——batch76 首跑 15/19 后死亡实证, 与 R142 compression 同源教训)；批76 全量 19/19 复证 pivot_n=1 真重锚。
- **README 30 批滚动制度 (R152b 用户钦定)**：README 能力段只保留最新 2 个轮段（整段完整能力列表），更早轮段整段撤出、按轮段归档 docs/changelogs/ (CHANGELOG-v0.11.0-RXXX-RXXX.md 格式, v7.14 亦在其中)；批次趋势行只留最新 2 批 + 归档链接；下次滚动: 批108。
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
