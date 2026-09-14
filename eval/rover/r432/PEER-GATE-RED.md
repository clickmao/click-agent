# R432 附注：门禁红项属对侧 R431 registry 行（本侧未改对侧产物）

## 机检事实（2026-09-14，本侧 R432 提交 `44c6f38` 后）
- `bash /tmp/gate_r429.sh` ⇒ **12/13**，唯一红项 = `VerificationFormTests.Registry_Exists_And_HasNoViolations`：
  ```
  r431.gate-role-growth-mount: covers 登记的路径不存在 'src/agent/IndustrialAgentV2.cs:gate-telemetry-shape' (R2c)
  r431.gate-role-growth-mount: covers 登记的路径不存在 'src/agent.modelqueue/ModelQueueRouter.cs:RecordPromptShape' (R2c)
  r431.gate-role-growth-mount: covers 登记的路径不存在 'src/agent.modelqueue/LocalGenerationPort.cs:TurnGateCounters' (R2c)
  r431.gate-role-growth-mount: covers 登记的路径不存在 'src/agent.roles/RoleGrowthLedger.cs:DomainCount' (R2c)
  r431.gate-role-growth-mount: covers 登记的路径不存在 'src/agent.tests/TurnGateGrowthMountTests.cs:9' (R2c)
  ```
- 该行由**对侧提交 `f319198`**（R431: role 额外数据有界挂载）引入：`git log -1 -S "r431.gate-role-growth-mount" -- docs/verification-registry.json` ⇒ `f319198`。
- 本侧行（`r432.turn-gate-discrimination-pair`，行 66）`covers` 全为**纯路径**（R2c 通过）：
  `eval/rover/r432/settle_r432.py` / `eval/rover/r432/run_arm.sh` / `eval/rover/r432/grid/task-r432dp2.json` / `src/agent.modelqueue/LocalGenerationPort.cs` / `src/agent/IndustrialAgentV2.cs`
- 其余两类形式校验在本侧提交后复跑：`DevPlanDocRefTests|SkillGeneralizationTests` ⇒ **7/7 绿**。

## 判定与处置
- `covers[]` 的 R2c 规则要求「单个真实存在的**路径**」；`路径:符号` 形式会被判为不存在 ⇒ 该行需**对侧自行**修正（例如改为纯路径，或把锚点移入 `capability` 文本）。
- **本侧不修改对侧 registry 行**（不越界、不改写他方产物）：仅登记事实、给最小修法建议；对侧作业活跃，预计由其下轮修复。
- 本侧 R432 的**能力登记不受影响**：行 66 合规、其 evidence_path 为 `eval/rover/r432/README-evidence.md`（存在）。

## 原始门禁输出（片段）
```
== 该行由谁引入 ==
f319198 R431: role 额外数据(成长经历)有界挂载进 r1 门判 + 挂载可机检
== 本侧行 66 covers ==
id r432.turn-gate-discrimination-pair | covers: ['eval/rover/r432/settle_r432.py', 'eval/rover/r432/run_arm.sh', 'eval/rover/r432/grid/task-r432dp2.json', 'src/agent.modelqueue/LocalGenerationPort.cs', 'src/agent/IndustrialAgentV2.cs']
== 逐类复核 ==
Test run for /home/agentuser/AgentFramework/src/agent.tests/bin/Release/net10.0/agentframework.tests.dll (.NETCoreApp,Version=v10.0)
A total of 1 test files matched the specified pattern.

Passed!  - Failed:     0, Passed:     7, Skipped:     0, Total:     7, Duration: 219 ms - agentframework.tests.dll (net10.0)
```
