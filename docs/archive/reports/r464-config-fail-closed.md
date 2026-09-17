# R464 · 本地判别通道「配置错配」fail-closed（消灭静默回退默认权重）

状态: 已完成 (R464) · 计划 `docs/plans/v0.83.0-r464-channel-config-fail-closed.md` · 判决 `eval/rover/r464/verdict-r464.json`
被测二进制: `/tmp/pub_r464/agenthost` (15,326,816 B, sha256 `381550e9dfe20bdc8b3f72ecb4fd52128dc7f8a90d8909d98840b0d330247578`, NativeAOT 发布 **0 IL 警告**)
网格/桩/role: `eval/rover/r438/grid/task-p12.json` / 同桩 `stub_openai.py` / role=`skeptic-growth.rbin`（Arole 与 B3B 逐字同 role）

## 1. 缺陷与修法（R463 首跑负控 VOID 的根因）

R463 的 BP 负控（配置 `model_path` 指向不存在文件）**没有失败**，读数 8 调用/20,484 tok 与 B3B 8 调用/20,487 tok 几乎逐位相同 ⇒ 负控失效（VOID）。根因不是负控设计，而是产品代码：

```csharp
// src/agent/extensions/ServiceCollectionExtensions.cs:300 (R413 原样)
var modelPath = lc.IsReady ? lc.ModelPath : baseOpts.ModelPath;   // 三态塌成两态
```

`IsReady = 非空 && File.Exists`。于是「配置**错配**」（显式声明了路径但文件不存在）与「配置**未声明**」不可区分，两者都被静默当成「未配置」→ 跑内置默认权重。判据面无法区分，因为运行时形状真的相同。

R464 改为**三态来源判定**（`src/agent.llamacpp/LocalChannelWiring.cs`；`LocalChannelConfig.Declared` 在 `ModelCatalog` 解析 `local:` 段时置位）：

| 来源态 | 条件 | 行为 |
| --- | --- | --- |
| 配置未声明 | 无 `local:` 段 / 无 `model_path` | 通道关闭（原语义不变） |
| 配置可用 | 声明且文件存在 | 通道启用，权重 = `ConfigPath`（原语义不变） |
| **配置错配** | 声明但文件不存在 | **显式告警 + 通道置不可用 + 降级远端**（fail-open 但可见；不再冒名默认权重） |

告警面（宿主 stderr，ASCII 标记，AOT 安全）：

```
[warn] R464 config_mismatch: local.model_path 不存在 /nonexistent/r464-cfg-nomodel.gguf ⇒ 本地通道置为不可用 (未回退默认权重 /home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf)
```

## 2. 四臂端到端读数（同网格 / 同桩 / 同 role）

| 臂 | 配置 | 远端调用 | token(桩口径) | 降幅 | 门判 Skip | 本地判决 | 本地 eval/gen | 告警 | 12 轮 ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Arole | 门关 + role on（分母） | 21 | 33,323 | — | 0 | 0 | — | 0 | 12/12 |
| **B3B** | **门开 + role on（已采用）** | **8** | **20,487** | **−38.5%** | 4（全 Ack 轮） | 4 | 1,370 / 8 | 0 | 12/12 |
| BP | cfg 错配，env 默认**存在** | 21 | 33,306 | −0.05% | 0 | 0 | 0 / 0 | 2 | 12/12 |
| BP2 | cfg + env 双缺（真缺模型） | 21 | 33,311 | −0.04% | 0 | 0 | 0 / 0 | 2 | 12/12 |

- **主判据 C5 PASS**：B3B 对 Arole 降幅 **38.52%**（≥30% 达标），远端调用 21 → 8。
- **C10（单一变量族，PASS）**：BP 与 B3B 同 role / 同 relation_judge / 同网格，唯一变量 = **本地通道可用性** ⇒ 降幅 **38.49%**。这条比 Arole 更干净（Arole 的 RJ=false 与 B3B 不同），登记为事后判据单列。
- **C3/C4 PASS**：错配臂留下 2 条告警，且读数**不再与 B3B 相同**（33,306 vs 20,487）。
- **C9 PASS（本地承重证据）**：门开臂 4 次 `gate:skip→local`，每次本地实算 **eval≈342 tok / gen 2 tok** ⇒ Skip 是「本地判决」而非「空跳过」。
- **跨版本等式（C8/C8b，PASS，改造零回归）**：R463≡R464 同名臂逐位相同 —— BP2 `21 / 33,311`、B3B `8 / 20,487`。同时 R463 BP `8 / 20,484`（静默跑默认 3B）→ R464 BP `21 / 33,306`，**冒名消失**是该修复的物理证据。

### 逐轮门判（B3B）

| 轮 | 用户消息 | 门判 | 依据 | 本地成本 |
| --- | --- | --- | --- | --- |
| 1 | 把构建命令写成一行。 | Pass | mechanical:pass→remote | — |
| 2–5 | 谢谢，收到。/好的，明白。/嗯嗯，知道了。/明白，多谢。 | **Skip** | gate:skip→local | eval 342/342/343/343, gen 2 |
| 6–9 | 再讲一遍。/讲细一点。/换个说法。/从头再说。 | Pass | mechanical:nonack→remote | — |
| 10–12 | 你上一条说 3 加 5 等于…/…说的数是九。/不对，你上一条不准确… | Pass | mechanical:nonack/pass→remote | — |

真诉求轮（6–12）零 Skip、零守卫否决、`quality_risk=0`；被门控的 4 轮全是驱动类 Ack（与用户口径「大部分时候我的回复仅是让你执行下一轮」对齐）。

## 3. 质量与代价（诚实边界）

- **质量面只做到「结构面」**：12/12 轮 ok、真诉求轮零 Skip、回复非空。**未做**回复质量打分（无人工/裁判评分），因此「回复质量不降」只能宣称到结构级别。
- **延迟代价（本轮新发现，量级不容忽视）**：门控轮的墙钟时间 **40.7 / 40.9 / 70.8 / 102.2 s**（B3B 总 256.0 s）vs 门关臂同期 **0.04–0.08 s**（总 1.1 s）。即：远端 token 降 38.5%，换来被门控轮 **+40~100 s** 延迟（3B 在 CPU、`gpu_layers:0`、每次本地调用含服务启停+权重量）。
- **分母口径**：token 数为**桩侧分词估计**（同桩同估计器跨臂可比），绝对值不等于真实供应商计费；未接真实远端供应商核对账单。
- **未测**：① 同臂复跑（本表无复跑臂 ⇒ 确定性只由跨版本等式 + R463 单跑支持）；② 本轮未重跑 B15/pf0 族（档位×前置门对照沿用 R463）；③ 未做进程级取证（本地算力为遥测口径反推，非 `ps`/`ss` 采样）。
- **单测**：全量 **1387/1388**；唯一失败 `ExecutorHardeningTests.FileLock_ConcurrentAppend_NoLoss_NoInterleave`（满载 120 段得 119，产物级偶发），**单跑 3/3 全绿**，与本轮改动（DI 接线/配置判定）无因果路径 ⇒ 登记为 R465 候选。形式门禁（VerificationForm/DevPlanDocRef/Registry/PlanNodeFormalGate）**60/60 非假绿**。

## 4. 预注册判据被证伪的处置

预注册的 **C6**（我写成「真缺模型 ⇒ `gate_events == 0`（门零决策）」）**FAIL**：实测门仍逐轮落 `local_turn_gate` 事件（12 条），只是全部 `Pass` 且 `basis=gate:degraded:failed_or_empty→remote`。即我预设的「零决策」形态与产品语义不符（产品语义 = 零 **Skip**、零本地算力；不是零遥测事件）。按判据纪律：**C6 保留 FAIL 不改写**，正确形态单列 `checks_posthoc`：

| 事后判据 | 结果 |
| --- | --- |
| C6′ 错配臂零本地判决/零本地算力/零 Skip/12 轮完成/告警可见 | PASS（BP 与 BP2 双绿） |
| C8 / C8b 跨版本确定性等式（零回归 / 增益可复现） | PASS（21/33,311；8/20,487） |
| C9 门控轮本地承重（eval 1,370 / gen 8 > 0） | PASS |
| C10 单一变量分母族降幅 ≥30% | PASS（38.49%） |

## 5. 交付物

- 代码: `src/agent.llamacpp/LocalChannelWiring.cs`(新) · `src/agent/extensions/ServiceCollectionExtensions.cs`(改) · `src/agent.modelqueue/ModelCatalog.cs`(改, `Declared`) · `src/agent.tests/LocalChannelWiringTests.cs`(新, 8 例机检)
- 器具: `eval/rover/r464/{run_arm.sh, settle_r464.py}`（settle 修哨兵混入求和 + `checks_posthoc` 单列）
- 证据: `eval/rover/r464/{verdict-r464.json, calls-*.jsonl, turns-*.jsonl, host-*.log, prov-*.json}`
- 登记: registry `r464.local-channel-config-fail-closed`(L2) / `r464.settle-sentinel-and-cross-round-determinism`(L1)

## 6. 下轮候选（R465）

1. **本地门延迟**：40–100 s/门控轮 ⇒ 需长驻/预热 + prompt cache 复用；目标「token 降幅不变、门控轮延迟 ≤10 s」。
2. **真诉求轮的可跳性**（用户令主战场）：现有 Skip 只落在 Ack 轮；下一步按需注入压前缀（97% 命中红线），把「不必要的远端请求」继续压。
3. **偶发失败单测**：`ExecutorHardeningTests.FileLock_ConcurrentAppend_NoLoss_NoInterleave` 满载丢失 1 段 ⇒ 需并发下可证（非重试掩盖）。
4. **分母口径升级**：接真实远端供应商账单/计费面核对桩侧 token 估计（当前为估计值）。
5. **复跑臂**：补 B3B/BP 同臂复跑，把「确定性」从事后等式升级为预注册判据。
