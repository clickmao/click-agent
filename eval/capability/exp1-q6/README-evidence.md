# EXP1-Q6 证据 · 全仓失效引用的四级归属复核

> 判据 (预注册于复核器头部) / 复核器: `eval/capability/exp1-q6/attribute_failed_refs.py` **attribute_failed_refs-v1.2.0**
> 输入: `eval/capability/exp1-q6/result_q6_before.json` (仪器 v2.3.0 读数, 未改动)
> 台账: `eval/capability/exp1-q6/attribution_q6_v120.json` · 自证: `selftest_q6_v120.json` (18/18 绿)

## 1. 结论 (读数)

- 仪器 v2.3.0 的全仓两桶 **逐条复核完毕**: `stale_path` **21** 条 / `relocated` **13** 条。
- `stale_path` 21 条 = **13 条「退役前成形」(历史留痕)** + **8 条「与退役同提交」(不可判/弃权)**;
  真·死引用 (`dead_after_delete`) = **0** 条, 口径冲突 (`no_deletion_commit`) = **0** 条。
- 涉及文件 **10** 个, 全部满足: 全树**无同名候选** (独立于仪器过滤面的 os.walk 复核) + 有**删除提交**且该提交是 HEAD 祖先。
- `relocated` 13 条 = **10 条定点可改 (唯一候选 + 行号/符号成立)** + **3 条写法漂移 (路径里含省略号)**。
- 复核器退出码 **0** (0 = 无缺陷); 自证 **18/18** 全绿。

### 1.1 删除侧外部真值 (stale_path)

| 删除提交 | 提交主题前缀 | 日期 | 引用条数 |
|---|---|---|---|
| `af9856b` | v0.23.0 R386/R387 | 2026-09-13 | 8 |
| `b00917c` | R408 | 2026-09-14 | 13 |

### 1.2 stale_path 逐条

| 定性 | 文档 | 行 | 路径 | 删除提交 | 行级锚 | 串级锚 | 锚来源 |
|---|---|---|---|---|---|---|---|
| retired_after_write | `docs/plans/v0.22.0-exp6-embedding-model-selection.md` | 23 | `src/agent.embedcpu/BgeCpuEmbedder.cs` | b00917c | f43711a | f43711a | both |
| same_commit_as_deletion | `docs/plans/v0.23.0-exp10-agent.rover-local-prover-engine.md` | 68 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| retired_after_write | `docs/plans/v0.23.0-exp10-agent.rover-local-prover-engine.md` | 76 | `src/agent.embedcpu/agent.embedcpu.csproj` | b00917c | af9856b | af9856b | both |
| retired_after_write | `docs/plans/v0.25.0-r399-probe-hardening-and-kpi.md` | 21 | `src/agent.rover/cli/ForwardCli.cs` | b00917c | 4cabcc5 | 4cabcc5 | both |
| retired_after_write | `docs/plans/v0.26.0-r400-rover-generation-chain.md` | 35 | `src/agent.rover/cli/ForwardCli.cs` | b00917c | f75e6f7 | f75e6f7 | both |
| retired_after_write | `docs/plans/v0.26.0-r400-rover-generation-chain.md` | 36 | `src/agent.rover/infer/ForwardPass.cs` | b00917c | 9b439a8 | f75e6f7 | both |
| retired_after_write | `docs/plans/v0.26.0-r400-rover-generation-chain.md` | 37 | `src/agent.rover/infer/KvCache.cs` | b00917c | f75e6f7 | f75e6f7 | both |
| retired_after_write | `docs/plans/v0.26.0-r400-rover-generation-chain.md` | 39 | `src/agent.rover/cli/RoverCli.cs` | b00917c | f75e6f7 | f75e6f7 | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 19 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 20 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 21 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 151 | `src/agent.embedcpu/GgufModel.cs` | b00917c | af9856b | af9856b | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 279 | `src/agent.rover/gguf/GgufReader.cs` | b00917c | 778e798 | 778e798 | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 280 | `src/agent.rover/gguf/GgufReader.cs` | b00917c | 778e798 | 778e798 | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 281 | `src/agent.rover/gguf/GgufReader.cs` | b00917c | 778e798 | 778e798 | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 282 | `src/agent.rover/gguf/GgufReader.cs` | b00917c | 778e798 | 778e798 | both |
| retired_after_write | `docs/reports/r385/capability-inventory.md` | 284 | `src/agent.rover/runtime/TensorResidency.cs` | b00917c | 778e798 | 778e798 | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 324 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 325 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| same_commit_as_deletion | `docs/reports/r385/capability-inventory.md` | 326 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |
| same_commit_as_deletion | `docs/reports/r385/consolidation-candidates.md` | 18 | `src/agent/registry/CapabilityPlugin.cs` | af9856b | af9856b | af9856b | both |

### 1.3 relocated 逐条

| 定性 | 文档写的路径 | 唯一候选(树内实际路径) | 文档 |
|---|---|---|---|
| fixable_direct | `src/agent.core/userinteraction/UserConfirmRequest.cs` | `src/agent/userinteraction/UserConfirmRequest.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.userinteraction/PromptPersistence.cs` | `src/agent/userinteraction/PromptPersistence.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.userinteraction/ConsoleUserInteraction.cs` | `src/agent/userinteraction/ConsoleUserInteraction.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.userinteraction/PromptPersistence.cs` | `src/agent/userinteraction/PromptPersistence.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.userinteraction/PromptPersistence.cs` | `src/agent/userinteraction/PromptPersistence.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.userinteraction/ConsoleUserInteraction.cs` | `src/agent/userinteraction/ConsoleUserInteraction.cs` | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| path_elision | `src/agent.core/.../TaskPlan.cs` | — | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| path_elision | `src/agent/.../EvidenceGate.cs` | — | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| path_elision | `src/agent.../PromptAuditEntry.cs` | — | `docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md` |
| fixable_direct | `src/agent.maf/MAFConfiguration.cs` | `src/agent/maf/MAFConfiguration.cs` | `docs/plans/v0.22.0-exp5-lesson-table.md` |
| fixable_direct | `src/agent/frontendapi/FrontendApiContract.cs` | `src/agent.frontendapi/FrontendApiContract.cs` | `docs/plans/v0.22.0-l2-capability-diff.md` |
| fixable_direct | `src/agent/modelqueue/ModelQueueRouter.cs` | `src/agent.modelqueue/ModelQueueRouter.cs` | `docs/reports/r385/chain-map.md` |
| fixable_direct | `src/agent.contextassembler/ContextAssemblerConfig.cs` | `src/agent/contextassembler/ContextAssemblerConfig.cs` | `docs/reports/r385/consolidation-candidates.md` |

## 2. 判据 (本轮新增的四级归属)

| 级 | 判据 | 取数 | 反面控制 |
|---|---|---|---|
| L-1 | 精确相对路径在 HEAD 内存在 | 版本库索引查询 | 存在路径不得被本桶收进 (`P1`) |
| L-2 | 全树**无过滤**同名搜索 (独立于仪器 `_rel_ok`) = 0 候选 | 自写目录遍历 | 存在文件必须 >0 命中 (`N2b`) |
| L-3 | `stale_path` 桶必须有**删除提交**, 且该提交是 HEAD 祖先 | 历史检索 + 祖先判定 | 从未入版本库的路径 ⇒ `never_tracked`, 不得判"真删" (`N1`) |
| L-4 | **时间轴**: 事实自身引入点 vs 退役点 | 行级历史追溯 + 串级首现(须跟随重命名) 双锚 | 真版本库夹具三样本必须落**三个不同类** (`T1/T2/T3`) |

分类次序 (先给"证否缺陷"的强证据, 再弃权, 最后才判缺陷):
`任一证据不晚于退役 ⇒ retired_after_write` → 否则 `有证据与退役同提交 ⇒ same_commit_as_deletion(弃权)`
→ 否则 `全部证据都晚于退役 ⇒ dead_after_delete`; 双锚互斥 ⇒ `axis_disagreement(弃权)`。

## 3. 自证 (18/18)

| 检查项 | 结果 |
|---|---|
| P1_live_path_in_HEAD | PASS |
| P2_deleted_has_commit_and_ancestor | PASS |
| N1_never_tracked_not_deleted | PASS |
| N2_unfiltered_zero_for_deleted | PASS |
| N2b_unfiltered_positive_control | PASS |
| F1_dead_after_delete | PASS |
| F2_retired_after_write | PASS |
| F3_axis_conflict_waived | PASS |
| F4_no_deletion_waived | PASS |
| F5_single_evidence_used | PASS |
| F6_same_commit_waived | PASS |
| F7_earlier_beats_same | PASS |
| F8_same_beats_later | PASS |
| P3_elision_bucket | PASS |
| N3_elision_negative_control | PASS |
| T1_fixture_pre_retire_is_history | PASS |
| T2_fixture_post_retire_is_defect | PASS |
| T3_fixture_same_commit_is_undecidable | PASS |

## 4. 复现命令 (逐字)

```
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --repo . --out eval/capability/exp1-q6/result_q6_before.json
python3 eval/capability/exp1-q6/attribute_failed_refs.py --repo . --selftest
python3 eval/capability/exp1-q6/attribute_failed_refs.py --repo . --result eval/capability/exp1-q6/result_q6_before.json \
        --out eval/capability/exp1-q6/attribution_q6_v120.json
```

## 5. 诚实边界

① 证据等级 **L1 静态机检** (无编译/测试/真机运行)。
② **"当前不成立" ≠ "写成时就错"**: 本轮的 0 缺陷是**第二判据** (`dead_after_delete`) 的读数, 不代表那 21 条引用在当下有效——
　其**当前无效性**已由 L-1/L-2/L-3 三项外部真值证成 (见上表), 只是**缺少"写作时即失效"的证据**。
③ 8 条「与退役同提交」是**弃权不是清白**: 一次提交既退役文件又写入文档时,
　"变更前勘查的记录"与"变更后残留"在时间轴上同形, 判据不可分 (要判别需变更前快照/变更描述, 时间戳无用)。
④ 时间轴锚点是**版本库历史**锚: 未入版本库的文档无锚 ⇒ 弃权 (`ambiguous_no_time_axis` 本档 0 条)。
⑤ 语料是**移动目标** (对侧作业在改 `src/`): 本轮读数与 HEAD 绑定; 复跑前先记 HEAD。
⑥ 本轮**三次被测测量层自身缺陷** (均先于结论修掉, 见 §7)。

## 6. 确定性复跑 (同输入两跑逐位相同)

`attribution_q6_after_docs.json` = 复核器在**含本附录的语料状态**上重跑同一输入的结果:
逐条类别 (21 stale + 13 relocated, 含文档路径与行号) 与 `attribution_q6_v120.json` **逐位相同**
(`stale {'retired_after_write': 13, 'same_commit_as_deletion': 8}` / `relocated {'fixable_direct': 10, 'path_elision': 3}`, `n_defects 0`)。双重作用: ① 复核器确定性成立;
② **本附录零 `src/` 路径字面量** ⇒ 未引入新引用 (仪器复跑对照: `stale_path 21→21` / `relocated 13→13` / `symbol_absent 65→65` / `stale_lines 4→4`)。

## 7. 测量层自捕 (先修仪器, 再谈被测)

| # | 版本 | 缺陷 | 症状 | 修法 |
|---|---|---|---|---|
| 1 | v1.0.0 | 时间轴锚点取**文档最后修改提交** (而非引用自身引入点) | 同一批 7 条被判 `dead_after_delete` | 锚点下沉到**行级历史追溯 + 串级首现** |
| 2 | v1.1.0 | 串级首现检索**未跟随重命名** ⇒ 返回重命名提交当"首次出现" | 1 条假红 (首现锚 = R392 重命名 20:49, 真值 = 原提交 19:26) | 检索加**跟随重命名**; 并新增「同提交」独立类 |
| 3 | v1.1.0 | 同一提交时"祖先判定"返回不可判 ⇒ 落到歧义分支, 理由文案与事实不符 | 理由写"锚点均不可得"而实际两锚都可得到 | 祖先判定返回三态 (早/同/晚) + 理由文案按事实更新 |
