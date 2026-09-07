# 动态打点测试评测回滚策略说明报告

> **文档性质**：AgentFramework 千轮迭代主控报告（随千轮任务持续更新，最新版本随每次提交推送 GitHub）。
> **主题（用户钦定 2026-09-07）**：针对用户话题倾向，围绕用户体验，使用动态打点策略，不断优化迭代 agent 功能。
> **恢复迭代入口**：上下文丢失后，读本报告 §7（迭代状态快照）+ `eval/results/mass_*.json`（自动镜像轮数据）即可继续，无需其他上下文。
> 最后更新：R131（2026-09-07）· commit 见 `git log --oneline -1`
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

- **主线进度**：R138-R153。R149 用户质疑整改（真断言族）；R151 pivot 判定闭环（真缺陷 56 KeyError 修复）；R152 收尾（phase report 3: batch62-78 187/187 + README 30 批滚动制度）；**R153 真缺陷 57 修复**：D4 gate 读 os.environ 致 reply_rel 整块静默失效（批79/80 n=0 实证，诚实缺省未破）→ gate 同源 load_env()，批81 同环境复验 n=11 avg 0.631 恢复。下一轮号 **mass_298**。
- **最近五批审计（批76-80）**：63/63 全绿（quick-11 子集 44/44）；tok/case 941→939→928→860 递降带内（全量批 1165 口径不同）；drift 全 1.0；suspects 0；D4 rel 修复前 n=0（缺陷 57）/修复后 n=11 avg 0.631。
- **R149 用户质疑结论**：TaskRelevanceChecker 组件能力真实（全量批 50/53 isolated=True score=2 实测）但判定空心成立——既往 C14/C15 expect 只有 llm:true，通过率对组件无证明力。修复后 C14 真断言批69-72 四连验 isolated=True score=2 PASS (4/4)。
- **R151 (pivot 判定闭环)**：C15 pivot_reanchor 升级为三重真断言 (不隔离+pivot_n≥1+新任务链产出)；pivot_n 打点消费建成 (goal/op=pivot, 真缺陷 45: init 缺键 KeyError——batch76 首跑 15/19 后死亡实证, 与 R142 compression 同源教训)；批76 全量 19/19 复证 pivot_n=1 真重锚。
- **README 30 批滚动制度 (R152b 用户钦定)**：README 能力段只显示最新 2 批，历史按轮段归档 docs/CHANGELOG-v0.11.0-R103-R127/R133-R142/R143-R152.md；批次趋势行只留最新 2 批 + 归档链接；下次滚动: 批108。
- **in-flight**：R153 收尾 → R154+ 候选：① 批 82+（quick-11 常态）② 批 85 五批审计 ③ K1 质量纵向 ④ 全量 19 批回归（批77 后首全量, 验 C15/pivot 链）⑤ 持续。
- **推送状态（R153c 已解）**：新 PAT 验证 200 OK scope=repo；积压 dc13413/1f8ff13/9a6d89a 已推上 remote (1f8ff13..424f2e6)，API 复核 remote=HEAD=424f2e6；一次性 URL 流程，config 零残留。旧 PAT 失效 (401) 弃用。
- **环境事实**（防重查）：bge=`/home/agentuser/.agentframework/models/bge-q8.gguf`（`.env.local` `AGENTFRAMEWORK_BGE_MODEL`，**cron/新 shell 须 export PATH="$HOME/.dotnet:$PATH" 否则 runner FileNotFoundError**；bge 路径勿依赖 os.environ——缺陷 57 教训，harness 统一走 load_env()）；3 key：kimi 负样本/glm 可用/deepseek 7.61 CNY；github 直连断→ghfast.top 代理推（>8min 假死勿中断）；telemetry 读用 utf-8-sig；`execute_code` 300s 上限→批测逐轮后台跑；**llm-service/llm.sock 已 R113 退场，sock 缺失=正常态勿重启**。
- **千轮口径**：RETIRED 轮诚实标注；全绿口径=排除 RETIRED；轮号唯一；每轮落盘+镜像。

## 8. 本报告的更新纪律

1. 每完成一轮（R1xx）若涉及打点/评测/回滚机制变化 → 更新对应章节；
2. 每 5 批 → 更新 §6 基线表 + §2 点位审计结论；
3. 每次回滚 → §4.3 历史记录追加；
4. 报告与代码同 commit 推送（保证 eval/results、台账、报告三者一致）；
5. **长期记忆分层纪律（2026-09-07 用户纠正后确立）**：记忆只装三类——①指针（本报告路径+恢复入口）②元规则（铁律/方法论，跨千轮不变）③活跃靶点（短周期，完成即清）。**轮次状态（R1xx 进度/commit/基线数字/下一轮号）一律不进记忆**，全下沉到本报告 §7 + 台账 + git，随 commit 滚动——否则到 R3000 时过时基线会污染新会话，且按轮追加会撑爆记忆预算。细节以本报告为准。**活跃靶点条目规范**：记忆里保留一条「当前活跃靶点」（下一优先级 2-3 项+一句话定性质疑点），**滚动替换、完成即清、禁止追加**——它是"下次醒来接着干什么"的最小指示，完整候选清单与细节仍以本报告 §7 为准。
