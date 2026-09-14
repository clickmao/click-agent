# R431 证据 — role 额外数据 (成长经历) 挂载进 r1 门判: 可机检 + 有界 + 无截断

生成方式: `eval/rover/r431/make_evidence_r431.py` 由机检产物 (prov/verdict/测试输出/发布日志/前置探针) 直接渲染,
**文档内所有数字均来自落盘读数, 无手抄**。结构化同源: `summary-r431.json`。

## 0. 前置事实 (改动之前, 机检)
- 真机臂角色 `skeptic.rbin` 容器 (magic `ARBL` + AES-GCM + gzip) 解出的 JSON 键 = `['id','name','profile','tokens']` —— **无 growth 键**:
  ```
id=skeptic name=疑问者 profile_len=70
growth_domains=0 {}
role_seed_sha16=0aa656fa7eafd93a
⇒ 域=0 ⇒ RenderForPrompt() 恒空串 ⇒ 门判挂载与不挂载逐位同一 (挂载在当前真实负载上不可测)
  ```
- 管道**早已**支持挂载 (`BuildPrompt` 内 `Clip(growthBlock, 300)`), 但调用点一直传 `null` ⇒ 挂载在真实负载上是空操作。
- 独立互证 (python 重建 vs 引擎渲染): 用源码字面量重建 `BuildPrompt`(msg=`好，按这个来。`, seed=`skeptic|`+profile),
  交 llama.cpp `/apply-template` 渲染, 得到 sha16 与 R430 真机遥测记录值 **逐位相同**:
  `prompt_sha=850f6cb17181a38f` (R430 记录 = 850f6cb17181a38f), `role_seed_sha=0aa656fa7eafd93a`。
  ⇒ 冻结基线成立, 且**反证 R430 时 growth 确为 null** (若曾挂载, 渲染串不可能同长同指纹)。脚本: `frozen_baseline.py`。

## 1. 本轮改动
| 文件 | 改动 |
|---|---|
| `src/agent/IndustrialAgentV2.cs` | 挂载点: `gateGrowthBlock = GrowthLedger?.RenderForPrompt()` + 传给 `JudgeTurnAsync`; 遥测新增 `gate_prompt_len/role_seed_chars/growth_chars/growth_lines`; 配置行新增 `role_growth_domains` |
| `src/agent.modelqueue/ModelQueueRouter.cs` | prompt 只构造一次, **形状读数取自实发文本** (二次重建会漂移), `TurnGate.RecordPromptShape(...)` |
| `src/agent.modelqueue/LocalGenerationPort.cs` | `TurnGateCounters` 新增 `LastPromptChars/LastRoleSeedChars/LastGrowthChars/LastGrowthLines` + `RecordPromptShape` |
| `src/agent.roles/RoleGrowthLedger.cs` | 新增 `DomainCount` (供配置行做挂载前置条件机检) |
| `src/agent.tests/TurnGateGrowthMountTests.cs` | 新增 9 条机检 (见下) |

## 2. 构建 (铁律: AOT + IL 告警 0)
- `$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r431` (不带 `-p:PublishAot`)
- 产物: `/tmp/pub_r431/agenthost`  bytes=15184624  sha256=ac62a739221f7b6bca04eddcf1b3ef5c…
- **IL 告警数 = 0**
- V0 形态自证 (env -i 直启 + IL 负控): `native_ok=True`, 负控拒绝执行 = `True` (`prov-C-k8r-g431.json` / `-b431.json`)

## 3. 测试读数
- 新增机检类: {'failed': 0, 'passed': 9, 'total': 9}
- 全量回归: {'failed': 0, 'passed': 1251, 'total': 1251}

机检类 9 条 = 冻结基线逐位 (`"<sha16>`) / 挂载可见 / 300 字符有界 / 挂载改变输入(负控) / 计数形状(挂载臂) /
计数形状(未挂载臂=基线) / 账本 `DomainCount`↔`RenderForPrompt` 一致 / 链侧调用点源码守卫(防再退回 `null`)。

## 4. 真机双臂 (唯一变量 = 角色是否携带成长域)
同网格 `k8r`、同二进制、同消息族 (`ack`), 仅角色文件不同:

| 臂 | 角色 | 启动时域数 | 门判 prompt 长度序列 | 挂载字符序列 | 判定 | 远端调用 | 远端 tokens | 门判闭合 | 截断 |
|---|---|---|---|---|---|---|---|---|---|
| `-g431` (挂载) | fixture (3 域) | 3 | [426, 426, 426, 426] | [70, 70, 70, 70] ([3, 3, 3, 3] 行) | ['Skip', 'Skip', 'Skip', 'Skip'] | 1 | 2030 | True | True |
| `-b431` (对照) | 真 `skeptic.rbin` (0 域) | 0 | [355, 388, 388, 388] | [0, 32, 32, 32] ([0, 1, 1, 1] 行) | ['Skip', 'Skip', 'Skip', 'Skip'] | 1 | 1994 | True | True |
| R430 基线 (挂载前) | `skeptic.rbin` | — | 无该字段 | 0 (未挂载) | ['Skip', 'Skip', 'Skip', 'Skip'] | 1 | 1996 | — | — |

对齐与归因: `alignment_ok=True/True`, `attribution_ok=True/True` (门判结果与回复形态交叉校验, 顺序分区不硬对)。

### 4.1 三条读数说明
1. **挂载真的生效** (不是「代码里有这行」): 挂载臂每次门判 `growth_chars=70`/3 行; 对照臂从第 2 次门判起 `growth_chars=32`/1 行
   —— 因为链自己在运行中写账本 (`IndustrialAgentV2.cs:1684 GrowthLedger.Record(verdict.Kind, domainKey)`),
   新接线**立刻消费了链自产的 role 额外数据**。prompt 长度差恒等于 `块长+1` (挂载追加一个换行), 与单测不变量一致:
   `[426, 426, 426, 426]` vs 基线 355 = 355 + 70 + 1 = 426 ✓。
2. **有界**: 块经 `RenderForPrompt(≤400)` + `BuildPrompt(Clip 300)` 双重截断 ⇒ 不可能挤爆生成预算 (R413 的截断教训)。
3. **不劣化**: 两臂判定 `Skip×4` 与 R430 基线一致; 远端调用 1 次 (机械门在第 1 轮放行, 与 r1 无关); 门判全部闭合 (`decided=true`, `raw_len>0`, 无截断标记)。

## 5. 诚实边界 (没测到什么就说什么)
- **本轮不宣称 token 下降**: `k8r` 网格是「重复认可」族, 本就不产生额外远端调用, 远端 tokens 2030 vs 1994 vs 基线 1996 属同量级 (差异来自远端上下文本身, 非挂载)。
  ≥30% 的验收需要**真假信息判别网格** (P 族假信息/纠错轮), 未在本轮跑。
- **挂载质量未测**: 未测「有成长域时 r1 判得更准」(需要标注真假信息网格 + 逐轮评分), 只测了「挂载生效/有界/不截断/判定不翻转」。
- **`role_growth_domains` 只在启动配置行读一次**: 运行中新增的域不会体现在该行 (逐轮真值见 `growth_chars_seq`)。启动读数为 {'g431': 3, 'b431': 0}。
- 对照臂第 1 次门判 `growth_chars=0` ⇒ 与冻结基线 `prompt_len=355` **逐位同长**, 但未逐字节比对 sha (遥测未落块文本; 下轮候选)。
- 全量测试曾出现 1 条**未归因**失败 `TelemetryPendingTests.Emit_Before_Configure_Is_Flushed_On_Configure` (单独跑 2/2 通过), 本轮改动不触及该路径; 第二次全量读数见 `test-out-r431-full.txt`。

## 6. 下轮候选
1. **真假信息判别网格** (P 族: 假信息/纠错/新诉求), 量化「挂载成长域」对判定准确率与远端调用数的影响 —— 这才是 ≥30% 验收的主战场。
2. 遥测补 `growth_sha16` (块指纹) ⇒ 把「未挂载臂逐位等于冻结基线」从同长升级为同指纹。
3. `role_growth_domains` 由一次性配置行改为逐轮携带 (与 `growth_chars` 同源)。
