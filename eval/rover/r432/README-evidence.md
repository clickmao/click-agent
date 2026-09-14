# R432 证据 — 门判**判别力**与**确定性**成对判据（残余带内）

本文件由 `make_evidence_r432.py` 从机检 JSON 生成（非手抄）：`verdict-C-r432dp1.json`（臂 1）、`verdict-C-r432dp2.json`（臂 2）、`prov-C-r432dp*-r432dp*.json`（形态闸）。

## 0. 撞号登记（R431 让号 → R432）

- 本侧起手时的占用序列读取被终端截断（只回 1 行）⇒ 曾以 R431 / v0.52.0 命名建器具；复核发现**对侧并发作业已占用 R431 与 v0.52.0**（本侧起臂时在途未提交；对侧随后提交为 `f319198`：`src/agent.modelqueue/LocalGenerationPort.cs`、`ModelQueueRouter.cs`、`src/agent.roles/RoleGrowthLedger.cs`、`IndustrialAgentV2.cs` 的门判遥测 `gate_prompt_len`/`role_seed_chars`/`growth_chars`/`growth_lines`，加 `src/agent.tests/TurnGateGrowthMountTests.cs` 与 `docs/plans/v0.52.0-r431-growth-mount.md`）。
- 处置：**本侧让号** ⇒ 轮号 R432、版本号 v0.53.0；r431 命名下的中止臂读数作废；对侧 `src/**`、对侧计划文档与对侧 `eval/rover/r431/**` 一字未动、未 add。
- 被测二进制 = `/tmp/pub_r430b/agenthost`（**提交态 `627dd23`** 构建）⇒ 与对侧 R431 改动无关；本轮不重发布 AOT。

## 1. 因果链

1. R429（`14b6156`）钉死决策路径前缀缓存 ⇒ 同文门判恒定、token −51.6%，但**判别力负控落空**（新诉求消息走 `[隔离任务]` 旁路，没进 r1 门）⇒ 「钉死后门仍能 Pass/Skip 正确」无证据。
2. R430（`627dd23`）补上**字节级确定性**（`raw_len_seq` 全等、4/4 同 sha）⇒ 遗留的不对称 = **确定性已证、判别力未证**（用户审计逻辑：只证「恒 Skip」= 空心指标风险）。
3. 本轮在同一二进制上构造**残余带网格**（机械词表覆盖不到的短消息：`好的`/`继续`/`重来一次`/`那个方案先放放`/`嗯`），把「同文重复」「对抗输入（语义带纠正/丢弃诉求但机械表未覆盖）」「机械负控」成对放入同一网格。
4. 仪器改进（相对 R430）：门遥测按 **时间窗**（`gate.ts ∈ [t_start,t_end]`）对齐到唯一轮，弃用 `secs>=5` 位置启发式；归因取桩侧 jsonl 的逐请求时间戳（外部真值）。
5. 臂 1 机检出**可达位偏移**：可达位 = 奇数位（seed 轮回复含问询 ⇒ 其下一轮被「ask 消费」进计划参数槽，实测 0.04 s、不进门）⇒ 臂 1 预注册族位落在被消费位；据此**在读数前**预注册臂 2 的**偏移无关网格**（每族 4 连排、负控置可达位）。

## 2. 判据与判决规则（预注册：`docs/plans/v0.53.0-r432-gate-discrimination.md` §2 / §2.1 / §3.1）

- C1 r1 路径判别力；C1p 组合级判别力；C2 同文逐位可复现（ack / cont）；C3 时间窗对齐 + 归因；C4 隔离旁路负控；C5 机械负控位不进 r1。

## 3. 臂 1（网格 `r432dp`，NS `-r432dp1`）— 族位错配读数

- （verdict 缺失）

## 4. 臂 2（网格 `r432dp2`，NS `-r432dp2`）— 族位校正后的裁决读数

| （verdict 缺失）| — | 未测到 |

## 4b. 通道分离后验（post-hoc，非预注册）

预注册 C3 用「窗内远端调用数」做归因 ⇒ 被证伪（Skip 轮也出现远端调用）。后验按桩侧**提示签名**分通道重做归因：
通道 G = 生成/回答通道（system 含「你是一个智能助手」）；通道 J = 关系判官通道（system 恰为「只输出一个字母。」）。

- **臂 1**：桩调用 2 = G 1 / J 0 / 其他 1；token G 1997 / J 0 / 其他 29；**Skip 轮数 8，其中带 J 调用 0 条**；`Pass ⇔ 窗内 G 调用` = True
- **臂 2**：桩调用 9 = G 1 / J 8 / 其他 0；token G 2000 / J 434 / 其他 0；**Skip 轮数 11，其中带 J 调用 8 条**；`Pass ⇔ 窗内 G 调用` = True

| 轮 | 族 | 判决 | secs | G | J |
|---|---|---|---|---|---|
| t1 | seed | Pass | 0.35 | 1 | 0 |
| t2 | ack | Skip | 39.89 | 0 | 0 |
| t3 | - | ungated | 0.0 | 0 | 0 |
| t4 | ack | Skip | 22.09 | 0 | 0 |
| t5 | - | ungated | 0.0 | 0 | 0 |
| t6 | cont | Skip | 16.78 | 0 | 0 |
| t7 | - | ungated | 0.0 | 0 | 0 |
| t8 | cont | Skip | 28.02 | 0 | 1 |
| t9 | - | ungated | 0.0 | 0 | 0 |
| t10 | adversarial_correct | Skip | 23.61 | 0 | 1 |
| t11 | adversarial_correct | Skip | 22.64 | 0 | 1 |
| t12 | adversarial_correct | Skip | 22.52 | 0 | 1 |
| t13 | adversarial_correct | Skip | 24.25 | 0 | 1 |
| t14 | adversarial_park | Skip | 24.89 | 0 | 1 |
| t15 | - | ungated | 0.04 | 0 | 0 |
| t16 | adversarial_park | Skip | 24.28 | 0 | 1 |
| t17 | - | ungated | 0.04 | 0 | 0 |
| t18 | filler | Skip | 21.25 | 0 | 1 |
| t19 | - | ungated | 0.0 | 0 | 0 |

- 结论：**生成通道零泄漏**（Skip 轮 G = 0）⇒ 门判 Skip 的省 token 机制成立；泄漏仅存在于关系判官通道（8 次 × ≈47 token = 434），因果指向「本地判官被门判占死单飞槽 ⇒ 回退远端」（R429 诚实边界 ③ 的因果坐实；未做消融，待下轮隔离）。

## 5. 形态闸（V0，fail-closed）

- 被测 AOT 原生 = True（15180528 B，sha `bb104dd7f2a021b0…`，`env -i` 自启 rc=0）
- IL 负控必拒 = True（rc=131）⇒ 形态判据有判别力

## 6. 诚实边界 / 排除项

1. 本臂与**对侧并发作业**（R431，后被其提交为 `f319198`）在同一台 2 vCPU / 3.57 GiB 机器上交错；两臂均在「安静窗口闸」（无对侧 dotnet/llama-server 且 MemAvailable ≥ 2650 MB，连续 2 次）后点火，但**未证明**整段测量期间零重叠。判据不含墙钟项（判定/指纹/对齐均由内容与外部真值决定）。
2. 被测二进制 = 提交态 `627dd23` 的 AOT；对侧 R431 改动当时仍在工作树（现已提交为 `f319198`）⇒ 本轮不重发布 AOT，也不宣称「与工作树一致」。
3. 遥测 `raw` 截断到 120 字符 ⇒ 前缀 sha 仅覆盖前 120 字符；`raw_len` 另行给出（本臂 raw_len 170 ⇒ 尾部 50 字符未逐字节覆盖）。
4. 判据只在**进了门的轮**上成立；未进门轮记 `ungated`（臂 1 的 18 轮中有 9 轮未进门）。
5. 「可达位偏移」（seed 后第 2 轮被 ask 消费）本身是**产品/驱动交互的实测性质**；臂 2 用 4 连排设计使其与本判据无关，但该偏移未被单独隔离验证。
6. 单机单次读数；不宣称跨机/跨构建/跨上下文长度可复现。

## 7. 复现命令

```bash
bash /tmp/r432_fire.sh    # 安静窗口闸 v2（排除空闲构建服务 MSBuild/VBCSCompiler）
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R432_NS=-r432dp1 bash eval/rover/r432/run_arm.sh C r432dp  47930 47931 /home/agentuser/AgentFramework/skeptic.rbin
bash /tmp/r432_fire2.sh   # 臂 2 点火闸
AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r430b/agenthost R432_NS=-r432dp2 bash eval/rover/r432/run_arm.sh C r432dp2 47930 47931 /home/agentuser/AgentFramework/skeptic.rbin
python3 eval/rover/r432/make_evidence_r432.py
```
