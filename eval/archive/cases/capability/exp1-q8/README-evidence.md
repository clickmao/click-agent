# EXP1-Q8 证据说明 · 仪器 v2.3.0→v2.4.1 符号存在性阶梯 (平行轴)

- 轮次: `EXP1-Q8` (60m 自检作业, **不占主线轮号**; 对侧 R441 真机臂同时在跑)
- 证据等级: **L1-static** (离线进程内复算 + 真实语料; 无编译/单测/AOT/真机运行 ⇒ 不得报 L3/L4)
- 计划文档: `docs/plans/v0.22.0-exp1-local-index-and-code-graph.md` 附录 I
- 语料: **179 文档 / 595 只读输入逐文件 sha256**; 引用 939 条

## 1. 本步做了什么 (一步, 不改判)

给仪器加一条**与主判据平行**的独立测量轴: 引用指向的文件里, 被引符号**以什么形态存在**。
五级 (`declared_type` > `declared_member` > `code_mention` > `noncode_mention` > `absent`) + `n/a_kind` 弃权。
代码面 = 剥离 `//` `/* */` 字符串/字符字面量 (逐行保长度) 后的文本。**候选 #3 要求 AST 级 ⇒ 本轮降级为词法级并登记**。
**不改任何 citation 的 verdict**; 生产源码零改动; 不跑 dotnet。

## 2. 读数 (预注册判据 → 结果)

| 判据 | 结果 |
|---|---|
| A1 细分不改判 (逐条 verdict + 既有字段) | **PASS** `verdict_diff=0` / `field_diff=0` / 键集合相同 |
| A2 新轴加性 | **PASS** v2.3.0 该字段 0 条 → v2.4.1 **466** 条 |
| A3 阶梯非平凡 | **PASS** 实级 5 级 / 符号 **570** 个 |
| A4 弃权单列 | **PASS** `n/a_kind = 1` (不进分母) |
| A5 三跑确定性 | **PASS** v2.4.0 存档 == v2.4.1 现场 (分布/桶面/弱边逐位) |
| G7 进闸 (all_pass) | **PASS** `gate_pass=true` `exit=0`; 仪器自检 **54/54 绿** |

- 桶面 (与 v2.3.0 逐位相同): `{"ok": 753, "symbol_absent": 66, "waived": 70, "stale_lines": 4, "retired": 21, "stale_path": 8}`
- 阶梯分布: `{"absent": 78, "n/a_kind": 1, "declared_member": 82, "noncode_mention": 29, "code_mention": 64, "declared_type": 316}`
- 新候选类: `code_mention 64 + noncode_mention 29 = 93` 条;
  其中主判据判 **`ok`** 的 = **25 条弱边** (符号只在注释/字符串面)。
- 弱边分布 (12 个被引文件):

```json
{
  "src/agent.frontendapi/FrontendApiContract.cs": [
    "req_id@docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:53"
  ],
  "src/agent.frontendapi/FrontendPromptService.cs": [
    "ask_id@docs/plans/v0.22.0-exp2-multi-option-ask-menu-protocol.md:105"
  ],
  "src/agent.gpu/cli/GpuCli.cs": [
    "VulkanNames@docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:288"
  ],
  "src/agent.llamacpp/LlamaCppTextEmbedder.cs": [
    "AGENTFRAMEWORK_BGE_MODEL@docs/plans/v0.22.0-exp1-local-index-and-code-graph.md:68",
    "NullTextEmbedder@docs/reports/bge/model-lineage-and-inventory-2026-09-14.md:54"
  ],
  "src/agent.modelqueue/ModelCatalog.cs": [
    "relation_judge@docs/plans/v0.47.0-r426-relation-judge-localization.md:50",
    "turn_gate@docs/plans/v0.47.0-r426-relation-judge-localization.md:50"
  ],
  "src/agent.modelqueue/ModelQueueRouter.cs": [
    "failed_or_empty@docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md:18"
  ],
  "src/agent/IndustrialAgentV2.cs": [
    "plan_executor_parallel@docs/plans/v0.22.0-exp3-step-alignment-validation.md:59",
    "loop_turn@docs/plans/v0.22.0-exp9-subtask-plan-routing-and-local-first.md:73",
    "empty_always@docs/plans/v0.22.0-r371-capability-probe-python-game.md:250",
    "recall_query@docs/plans/v0.42.0-r421-polarity.md:18",
    "correction_judge@docs/plans/v0.47.0-r426-relation-judge-localization.md:53",
    "dropped_chars@docs/plans/v0.59.0-r439-domain-extension.md:18",
    "local_gate_skip_history@docs/plans/v0.59.0-r439-domain-extension.md:18",
    "persisted_chars@docs/plans/v0.59.0-r439-domain-extension.md:18",
    "would_be_chars@docs/plans/v0.59.0-r439-domain-extension.md:18"
  ],
  "src/agent/contextassembler/ContextAssembler.cs": [
    "_queryEmbedding@docs/reports/function-map-R326.md:288"
  ],
  "src/agent/extensions/ServiceCollectionExtensions.cs": [
    "OpenAILLMCaller@docs/reports/r385/chain-map.md:51"
  ],
  "src/agent/intent/PlanRoutePolicy.cs": [
    "text_processing@docs/reports/r385/capability-inventory.md:56",
    "verify_local@docs/reports/r385/capability-inventory.md:56"
  ],
  "src/agent/intent/PlanRunner.cs": [
    "AGENTFRAMEWORK_PLAN_EXEC@docs/reports/r385/chain-map.md:127",
    "AGENTFRAMEWORK_PY_RUN@docs/reports/r385/chain-map.md:128"
  ],
  "src/agent/registry/CapabilityScanner.cs": [
    "RegisterCapability@docs/reports/r385/capability-inventory.md:24",
    "RegisterCapability@docs/reports/r385/consolidation-candidates.md:19"
  ]
}
```

## 3. 测量层自查 (先怀疑测量, 再谈被测)

抽检 4/25 条弱边人工复核 (全文/代码面逐行对照), **全部为真**:

| 符号 | 被引文件 | 真实出处 | 阶梯判定 |
|---|---|---|---|
| `req_id` | `src/agent.frontendapi/FrontendApiContract.cs` | `///` 文档注释 + 字面量 `"req_id"` (JSON 键名) | `noncode_mention` ✓ |
| `RegisterCapability` | `src/agent/registry/CapabilityScanner.cs` | 两处**注释** | `noncode_mention` ✓ |
| `AGENTFRAMEWORK_BGE_MODEL` | `src/agent.llamacpp/LlamaCppTextEmbedder.cs` | **环境变量名字符串** | `noncode_mention` ✓ |
| `_queryEmbedding` | `src/agent/contextassembler/ContextAssembler.cs` | **R326 退役注释** | `noncode_mention` ✓ |

按类归纳 25 条弱边: ①遥测事件/键名 (loop_turn / turn_gate / relation_judge / recall_query / correction_judge /
req_id / ask_id / dropped_chars / text_processing / verify_local / failed_or_empty / plan_executor_parallel /
empty_always) ②环境变量名 (AGENTFRAMEWORK_PLAN_EXEC / AGENTFRAMEWORK_PY_RUN / AGENTFRAMEWORK_BGE_MODEL)
③注释里的历史符号 (RegisterCapability / _queryEmbedding / NullTextEmbedder)。

**本轮自捕的测量层缺口**: 直接调用 `symbol_face(sym, None, text)` 会抛 `TypeError`
(临时复核脚本把 `src/agent/intent/` 误写成 `src/agent.intent/` 触发; 生产路径 `faces_for` 本有守卫)。
"测不到"必须**出声弃权**而非崩溃 ⇒ 加防御守卫 (None ⇒ `n/a_kind`), 升版 **v2.4.1**, 并**三跑重跑复核**。

## 4. 仪器自检 (两侧夹具)

## 3b. 归档卫生 (本轮自捕)

v2.4.0 首次跑把 `--out` 指向了 `eval/capability/exp1-q7/` (上一轮的归档目录) ⇒ 该目录的 `citations.jsonl`
被本轮的 v2.4.0 输出**覆盖**。当场 `git checkout --` 还原 (Q7 归档回到 HEAD 版本), 本轮全部产物改落 `exp1-q8/`。
教训: 归档目录**按轮次隔离**, 新轮的仪器产物不得写进上一轮归档 (同名文件即覆盖, 与被测无损但证据混淆)。

`--selftest` **54/54 绿, exit 0** (v2.4.0 新增 17 项):
五级各一 (F1–F6) / `new Foo(` 不得判声明 (F7 负控) / 剥离**保行数** (F8) /
**注释里的声明形态不得算声明** (F9) / **字符串里的声明形态不得算声明** (F10) /
端到端四级 (F11–F14) / **细分不改判**两侧 (F15 `ok` 保持 / F16 `symbol_absent` 保持) / 阶梯非平凡 (F17)。

## 5. 诚实边界

1. **L1 静态**: 无编译/单测/AOT/真机运行。
2. **词法级非 AST**: 剥离是状态机近似 (撇号在非字面量语境会吞到下一个撇号; 嵌套块注释不建模) ⇒
   `declared_member` 是**启发式**; 该轴只用于**分类弱边**, 不作"引用错误"的结论。
3. **阶梯只回答"在被引这一个文件里的形态"**: `noncode_mention` ≠ 缺陷 (符号可能在别处有真声明);
   本轮**没有修好任何一条** (含 H.5 第 4 点的 66 条 `symbol_absent`: 它们在全文也不存在 ⇒ 新轴仍给 `absent`, 与旧结论一致)。
4. **语料是移动目标** (对侧主线在改 `src/`/`docs/`; 本轮 179 文档 vs Q7 的 178) ⇒ 读数绑定当轮语料;
   确定性由**同进程 A/B** + 输入指纹消解, 不做"文件不动"的假设。
5. **形式校验本轮未跑**: 对侧 R441 真机臂在跑 (`/tmp/pub_r438/agenthost` AOT + llama-server) ⇒ 按并发纪律本侧不跑 dotnet;
   且改动面 = `eval/` 探针 + 计划文档,**未触及** `docs/verification-registry.json` 与 `skills/` ⇒ 触发器未命中。
   列为**对侧空闲后即跑**项。

## 6. 复现命令

```bash
cd /home/agentuser/AgentFramework
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --selftest                 # 54/54
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --repo . \
        --out eval/capability/exp1-q8/attribution_q8_symbol_ladder.json               # gate_pass=true, exit 0
python3 eval/capability/exp1-q8/ab_compare.py                                         # A1–A5, exit 0
```
