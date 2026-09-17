# R463 · 本地判别通道切换到 Qwen2.5-3B-Instruct Q4_K_M（用户令）+ 冗余模型清理

状态: 已完成 (R463) · 计划 `docs/plans/v0.82.0-r463-local-gate-3b.md` · 判决 `eval/rover/r463/verdict-r463.json`

## 1. 用户令与前置证据

用户令（逐字）：**"改用3b 并且 删除多余模型 3b q4"**。
前置：R462-W 权重档位探针 —— 现役 1.5B-Q4 对「继续下一轮」恒判 S（假跳 14/14）不合格；`Qwen2.5-3B-Instruct-Q4_K_M` 假跳 0/14、漏跳 0/14、gen 2 token/次、确定性 28/28 逐位复现（`docs/reports/r462-weight-probe.md`）。

## 2. 端到端读数（同网格 p12 / 同桩 / 同 role / 同二进制 `/tmp/pub_r463/agenthost`）

单变量：**模型档位**（1.5B vs 3B）× **前置门**（默认 on / 关）。

| 臂 | 配置 | 远端调用 | token(桩口径) | 降幅 vs A | 门判 Skip | 假跳(真诉求判 Skip) | 守卫否决 | 质量风险 | 12 轮 ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 门关（分母） | 12 | 31,093 | — | 0 | — | 0 | 0 | 12/12 |
| B15 | 1.5B + 前置门**开** | 8 | 20,487 | −34.1% | 4（全 Ack） | 0 | 0 | 0 | 12/12 |
| **B3B** | **3B + 前置门开（已采用）** | 8 | 20,487 | **−34.1%** | 4（全 Ack） | 0 | 0 | 0 | 12/12 |
| B15pf0 | 1.5B + 前置门**关** | 16 | 21,735 | −30.1% | 8 | **3** | 3 | 0（守卫兜住） | 12/12 |
| B3Bpf0 | **3B + 前置门关** | 16 | 21,735 | −30.1% | 4 | **0** | 0 | 0 | 12/12 |
| BP | 配置模型缺失（静默回退默认 ⇒ 3B） | 8 | 20,484 | −34.1% | 4 | 0 | 0 | 0 | 12/12 |
| BP2 | **真缺模型**（cfg+env 双缺，负控） | 21 | 33,311 | **−7.1%** | 0（全降级） | 0 | 0 | 0 | 12/12 |

### 逐轮门判（前置门关，单变量 = 模型）

| 轮 | 用户消息 | 1.5B 原始判决 | 3B 原始判决 |
| --- | --- | --- | --- |
| 2–5 | 谢谢，收到。 / 好的，明白。 / 嗯嗯，知道了。 / 明白，多谢。 | Skip ✓ | Skip ✓ |
| 6 | 再讲一遍。 | Pass | Pass |
| 7 | 讲细一点。 | **Skip ✗（守卫否决）** | Pass ✓ |
| 8 | 换个说法。 | Pass | Pass |
| 9 | 从头再说。 | **Skip ✗（守卫否决）** | Pass ✓ |
| 10 | 你上一条说 3 加 5 等于 9，对吧？ | Pass | Pass |
| 11 | 你上一条说的数是九。 | **Skip ✗（守卫否决）** | Pass ✓ |
| 12 | 不对，你上一条不准确，请重新确认。 | Pass | Pass |

## 3. 机制事实（本轮实测）

1. **默认面上模型档位不产生差异**：前置门开时 1.5B 与 3B 逐位同读数（8 调用 / 20,487 tok / 34.11%）—— 省 token 的承重结构是**机械 Ack 规则 + 前置门**，不是模型。
2. **换 3B 的价值在窄带**：前置门关时 1.5B 在真诉求上 3 次假跳（全靠 `skip_rejected_nonack` 守卫兜），3B 0 次 ⇒ 纵深防御，把守卫的事前移给模型判对。
3. **输出形状**：3B 每判 = 2 token / raw 1 字符；1.5B = 58–275 token 思考链 / raw 112–483 字符（判据面必须做「闭合标记后结论区」启发式解析）。
4. **本地成本**：3B 门判 prompt 342–343 token（每次全量评估，`cache_n=0`）；1.5B 316–317 token。
5. **延迟**：3B 门判 ≈ 30–60 s/轮（ctx 4608 / 2 vCPU）vs 1.5B 12–27 s/轮；3B 自身只生成 2 token，时间几乎全在 prompt eval。
6. **负控语义**：模型不可用 ⇒ 全部降级 Pass（零假跳、质量不退化），但**净亏 7.1%**（21 次远端调用 vs 分母 12）⇒ fail-open 有开销。

## 4. 新发现（缺陷候选，R464）

**配置指向不存在的模型会静默回退到默认权重**：`src/agent/extensions/ServiceCollectionExtensions.cs:300`
`ModelPath = lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` —— `lc.IsReady=false`（模型文件缺失）时不报错，直接改用 env/默认路径。本轮首次 BP 负控因此实际跑了 3B（读数与 B3B 逐位相同）⇒ 判定 **VOID**，重做 BP2（cfg+env 双缺）才得到真负控。
风险：运维误删/改名权重 ⇒ 产品静默换模型，遥测仅 `local_channel_ready=False` 一处线索。

## 5. 冗余模型清理（用户令；先落 bytes+sha256 台账再删）

| 路径 | bytes | sha256[:32] |
| --- | --- | --- |
| /tmp/models/r1-distill-qwen-1.5b-q4km.gguf | 1,117,320,800 | 1741e5b2d062b07acf048bf0d2c514da |
| /tmp/models/r1-distill-1.5b-q8.gguf | 1,894,532,192 | 166baa90e6a963de31a7713ff034f823 |
| /tmp/models/qwenpaw-flash-2b-q4km.gguf | 1,560,460,928 | fb733894f63e3b17bf539f1a1760e754 |
| /tmp/models/qwen2.5-3b-instruct-q5km.gguf | 2,438,740,384 | 2c63dde5f2c9ab1fd64d47dee2d34dad |
| **合计释放** | **7,011,054,304 B（6.53 GiB）** | — |

保留：`~/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf`（2,104,932,768 B / sha256 `626b4a6678b86442240e33df819e0013`）+ `bge-q8.gguf`（嵌入器）。磁盘 `/` 7.6G → 14G。

副作用（诚实）：B15/B15pf0 两臂（1.5B 对照）删除后**不可原地复跑**；其 calls/turns/遥测档案已入库，权重 sha 已登记，重跑须按 sha 重新下载。

## 6. 证据路径

- 计划 `docs/plans/v0.82.0-r463-local-gate-3b.md`；本报告 `docs/reports/r463-3b-gate-adoption.md`
- 臂执行器 `eval/rover/r463/run_arm.sh`（含 `BP2` 负控修正注记）；结算 `eval/rover/r463/settle_r463.py`
- 判决 `eval/rover/r463/verdict-r463.json`；桩侧逐请求 `eval/rover/r463/calls-*.jsonl`；逐轮 `eval/rover/r463/turns-*.jsonl`；遥测 `eval/rover/r463/run-*/data/telemetry/host.jsonl`
- 形态闸 `eval/rover/r463/prov-*.json`（V0-a 原生=True / V0-b 负控有判别力=True）
- 删除台账 `eval/rover/r463/deletion-ledger.json`

## 7. 判据裁定与契约边界修订

**预注册判据被证伪（事后修订）**：原判据 4「BP（3B 路径不存在）⇒ 门零决策、读数与 A 逐位一致」不成立 ——
① 首跑 BP 仅 cfg 缺 ⇒ `ServiceCollectionExtensions.cs:300` 静默回退默认权重，实际跑了 3B（读数与 B3B 逐位相同）⇒ 负控 **VOID**；
② 真负控 BP2（cfg+env 双缺）⇒ 全降级 Pass、0 Skip（增益归零）**但 21 调用 / 33,311 tok = −7.1%**（重试开销）⇒ 非「与 A 逐位一致」。
修订判据：**负控 = 增益归零（0 Skip）∧ 质量不退化**；7.1% 重试开销单列 `checks_posthoc`（registry `r463.local-gate-model-switch`）。

**R351 机检测试修订**：`FreeApiModelsTests.Yaml_Stripped_OfRemovedSources` 原含 `Assert.DoesNotContain("\nlocal:", yaml)`（R351「删本地推理通道段」）。与 R351 口径澄清（"r351移除的是本地llm使用，而新增的r1的使用是计划中…的一个节点"）冲突 ⇒ 删该行，边界改由 `Yaml_LocalBlock_DiscriminatorOnly` 机检（`allow_general: false` / `turn_gate`+`relation_judge`+`model_path` 显式 / 绝对 `.gguf` / 块内无 `chat` / 权重 >100 MB 若在盘）。详见计划 `docs/plans/v0.82.0-r463-local-gate-3b.md` §9。
