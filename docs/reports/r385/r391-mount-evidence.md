# R391 · agent 挂载证据 (C7 本地形式化验证节点 / C8 条件前缀契约注入)

- 轮次标签: `R391`
- 日期: 2026-09-13
- 状态: 已交付 (待本地 commit)
- 探针: `/tmp/r391probe/{r391probe.csproj,Program.cs}` —— **用生产组合根** `AddAgentFramework()` 装配, 不手搓对象图
- 原始输出: `/tmp/r391/evidence.log`

## 1. 为什么这两件事绑定在一起 (因果链)

C8 注入的契约要求模型把形式化断言写进 `clickproof` 围栏; C7 的执行器/路由必须**认同一套围栏语义**才能消费它。
若两侧各写一份解析器, 就会出现"注入了却读不到"的静默断链 ⇒ 本轮的单一事实源:
`ClickProofFence.Language`(围栏标识) 与 `ClickRoverSegmentPlugin.PluginId`(在场判据) 被**注入侧与消费侧同时引用**, 并有同源机检
(`FormalPromptContractTests.Contract_Ids_Match_Consumer_Side`)。

## 2. C8 · 静态前缀条件注入 (在场才注入)

判据: `SessionBaseline.Build(root, formalPluginPresent)`; 缺省重载 ⇒ 不在场 ⇒ **与 R380 前缀逐字一致** (零 token 负担)。
两槽缓存 (槽0=不在场 / 槽1=在场) —— 单槽会把两种前缀串味, 机检 `Two_Slots_Do_Not_Bleed_Across_Call_Order` 覆盖。

真机 (生产 DI) 原始行:

```
A_plugins=[ui-capture|code-review|agent.rover.formal|python-artifact]
A_formal_present=True
A_prefix_has_clickproof=True absent_has_clickproof=False
A_prefix_chars=2800->3391 delta_tokens_est=358
```

| 口径 | 值 |
|---|---|
| 前缀字符数 (不在场 → 在场) | 2800 → 3391 |
| 增量字符 | +591 |
| 增量 token (估算口径, 非分词器实测) | +358 |
| 不在场前缀是否含契约 | 否 (逐字不变) |
| 契约段是否含工作区路径 | 否 (机检 `Contract_Text_Is_Constant_And_Leak_Free`) |

注: 增量是**固定常量**, 进静态前缀即被 prompt cache 覆盖一次, 之后每轮命中。

## 3. C7 · 本地形式化验证节点 (零 token)

### 3.1 路由 (机器可读围栏 ⇒ 本地, 不靠自然语言关键词)

```
C_route=n1 intent=general location=Local exec=formal.verify
C_route=n2 intent=general location=Local exec=formal.verify
```

判据 = `PlanRoutePolicy.CarriesFormalClaim(node.Text)` ⇒ `ClickProofFence.ExtractTrimmed` 命中**或** `FormalVerifyExecutor.LooksLikeContract`。
负控: ```python 围栏 / 自然语言散文 ⇒ 不判本地 (机检 `Fence_Semantics_Are_Shared_With_Routing_Predicate`)。

### 3.2 执行 (真计划, 容器内无任何 LLM 调用面)

```
C_run_state=Finished
C_node=n1 loc=local exec=formal.verify state=Completed tokens=0
C_node=n2 loc=local exec=formal.verify state=Failed tokens=0
C_n1_proved=True n2_blocked=True total_llm_tokens=0
```

- `n1`: `premise x>=0 ∧ x<=10 ⊢ x<=20` ⇒ **Proved** ⇒ Completed。
- `n2`: `premise x>=0 ⊢ x>0` ⇒ **Refuted** ⇒ Failed (未证明绝不放行), 反例随 `PlanNodeFormalGate.BlockMessage` 同源文案回注。
- `total_llm_tokens=0`: 容器里**没有**任何 LLM provider 参与; 若误判远程, 该节点必然硬失败。

### 3.3 消费侧恒等透传 (插件绝不改写模型正文)

```
B_segment_identity=True reports=Refuted/allowed=False
```

DI 解析出的**真实插件实例**处理含围栏段: 返回值与入参逐字相等 (`==` 判定), 裁决只落账 (`DrainReports`), 正文一字不改。
经真实 `ResponseSegmentRouter` 的端到端同口径 (机检 `Real_Router_Output_Is_Byte_Identical_To_Input`)。

## 4. 机检 (26 例, 全绿) + 全量回归

**全量**: `env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj -c Release`
⇒ **Failed: 0 / Passed: 1051 / Total: 1051 / Duration: 27 s**（上一基线 1025 ⇒ 净增 **26** = 本表三套件, 与 `--list-tests` 计数逐项相符: 7+8+11=26）。
日志: `/tmp/r391/full_test.log`（全量）/ `/tmp/r391/list_tests.log`（逐套件计数）/ `/tmp/r391/evidence.log`（真机探针原始输出）。

| 套件 | 例数 | 覆盖的可证伪点 |
|---|---|---|
| `FormalPromptContractTests` | 7 | 不在场逐字不变 / 在场进入前缀且增量有界 / 两槽不串味 / 契约恒定无泄漏 / 同源标识 / 整词匹配 |
| `ClickRoverSegmentPluginTests` | 8 | 非围栏段恒等透传不误触发 / Proved 放行 / Refuted 阻断但正文不改 / Unknown·空段分别记弃权与 absent / DrainReports 取即清 / 真实 Router 逐字 / 围栏语义与路由谓词同源 + 负控 |
| `FormalVerifyExecutorTests` | 11 | 四态不混算 / Unknown 弃权但**不放行** / 缺失≠错误且零 LLM 追问 / 显式 no_formal / 上游围栏回退 / 裸契约行 / 登记表↔实现同源与路由可达 / 提取器语义 + 负控 |

关键负控 (有判别力的证据): `Contains` 类断言在 **Unknown 案例上先红过一次** —— 执行器当时只输出
`disposition=Abstained` 的枚举名, 没有闸门自己的中文分类 "弃权" ⇒ 改为复用 `PlanNodeFormalGate.BlockMessage`(同源文案) 后转绿。
这说明该断言确实绑定了组件真实行为, 不是空心判定。

## 5. 诚实边界

1. 存量 KPI 口径未因此改变: 本轮**不宣称** DCR 达标 —— FAVA 的 DCR 公式/分母/弃权处置仍不可得 (T1–T4 开放), 仍须双口径敏感性分析。
2. `Unknown ⇒ 节点 Failed` 是**执行策略** (未证明不放行); 与 DCR 台账里 "Unknown 计合规(弃权)" 是两个层级的口径, 不可混算。
3. 上游围栏回退 (executor 支持) 与路由判据 (只看本节点正文) **不同宽**: 若要节点被自动判本地, 断言必须落在本节点正文 —— 该要求已写进 C8 契约第 5 条, 但**模型是否照做尚未在真机上验证** (需带 LLM 的端到端轮次)。
4. token 增量为**估算** (中文 ~1 token/字, 非中文 ~1/4 字符), 非分词器实测。
5. 段插件挂载可用 `AGENTFRAMEWORK_FORMAL_SEGMENT=0` 关闭 (缺省开); 本报告未测关闭态在真实会话中的表现。
