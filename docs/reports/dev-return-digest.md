# 开发侧回流 digest（机械生成 · 单页）

> 生成器: `scripts/dev_return_digest.py` · 本文件**不产生新读数**，只汇聚已有外部真值产物与台账；
> 未标注状态的 D 条目渲染为「(未标注)」，不猜测。用途：给开发侧（assistant）下轮上下文一个可复验的唯一入口。

## 1. D 断链点（源: `docs/plans/v0.22.0-r371-capability-probe-python-game.md`）

| D | 标题 | 状态 | 源行 |
|---|---|---|---|
| D1 | 空正文被判成功 | 已修 | L24 |
| D2 | 发布产物不自带 config | 已修 | L43 |
| D3 | 运行结果回流闭环 —— 失败输出回流 + 有界修复 + 复检 | (未标注) | L192 |
| D4 | 裸代码 → 落盘/校验/运行 链全程不触发 | 已修 | L76 |
| D4-b | v2 字符串字面量感知 + 机制归因 | (未标注) | L116 |
| D5 | 运行级验证选参 + 结论上屏 | 已修 | L89 |
| D7 | 真机验收 | (未标注) | L235 |
| D8 | 策略实现正确但**接线缺口** → 首轮预算策略是死代码 | (未标注) | L155 |
| D9 | 经验落库形态 = **思考逻辑 skill | (未标注) | L176 |

## 2. 探针裁决（源: `eval/rover/*/verdict*.json` + `eval/capability/*/verdict*.json`）

| 目录 | 裁决文件 | verdict | 判据数 | 来源键 |
|---|---|---|---|---|
| r371d2 | verdict-r371d2.json | **pass** | 6 | `assertions` |
| r371d7 | verdict-r371d7.json | **PASS** | 5 | `arms` |
| r412 | verdict.json | **NO_CONTENTION** | 4 | `bool_fields` |
| r413 | verdict-r413.json | **PASS** | 7 | `gate` |
| r415 | verdict-r415.json | **PASS** | 22 | `checks` |
| r424 | verdict-r424.json | **PASS** | 3 | `bool_fields` |
| r425 | verdict-r425-b2.json | **PARTIAL** | 0 | `n/a` |
| r426 | verdicts.json | **?** | 0 | `n/a` |
| r429 | verdict-C-k8p-r429post1.json | **?** | 4 | `bool_fields` |
| r429 | verdict-C-k8r-r429post1.json | **?** | 4 | `bool_fields` |
| r429 | verdict-C-k8r-r429post2.json | **?** | 4 | `bool_fields` |
| r429 | verdict-C-k8r-r429pre1.json | **?** | 4 | `bool_fields` |
| r429 | verdict-r429.json | **?** | 0 | `n/a` |
| r421 | verdict-r421.json | **PASS** | 13 | `checks` |
| r422 | verdict-r422.json | **PARTIAL** | 8 | `checks` |
| r423 | verdict-r423-run1-predictor-error.json | **FAIL** | 7 | `checks` |
| r423 | verdict-r423.json | **PASS** | 9 | `checks` |
| r428 | verdict-r428.json | **PASS** | 0 | `n/a` |

**正文提及但无独立小节的 D 编号**（文档缺口, 不猜测其状态）: D6(L237), D9-a(L182)

## 3. 探针分数（质量；源: `data/probe/probe-*.json`）

打分单元 = **整题全对**（该题全部隐藏用例通过才算过）；`rate` 为用例级率（旁读）。
**饱和** = 整题全对 ∧ 用例级率均为 1.0 ⇒ 该题集对本解法已到天花板，**不能再用于度量质量**（需换更难族）。

| 文件 | 解法 | 题集 | 题数 | 整题全对 | rate(用例级) | 失败模式 | 判定 | tokens/题 | tokens/满分题 | turn≤ | 墙钟均(ms) | 过程 n/a |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `probe-agent-seed20260913.json` | agent | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-agent-seed419-r419bagent-b09141437-t2.json` | agent | program seed=419 | 3 | 3/3=1.0000 | 1.0000 | {"ok": 3} | **饱和** | 11911.3 | 11911.3 | 1 | 144960 | 0 |
| `probe-agent-seed419-r419bagent-b4095015-t2.json` | agent | program seed=419 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | 9121.5 | 9121.5 | 1 | 101595 | 0 |
| `probe-agent-seed419-r419dagent-b3092030-t2.json` | agent | program seed=419 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | 10495.0 | 10495.0 | 1 | 92956 | 0 |
| `probe-agent-seed420-r419cagent-b2091515-t2.json` | agent | program seed=420 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | 9217.7 | 9217.7 | 1 | 93357 | 0 |
| `probe-m6-agent.json` | agent | both seed=0 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-m6-hardcode.json` | mutation:hardcode | program seed=20260913 | 3 | 0/3=0.0000 | 0.1818 | {"partial": 3} | 非饱和 | n/a | n/a | - | n/a | 3 |
| `probe-m6-oracle.json` | oracle | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-mutation:delayfix-seed419-r419bctlpos-b09141437-t2.json` | mutation:delayfix | program seed=419 | 3 | 3/3=1.0000 | 1.0000 | {"ok": 3} | **饱和** | n/a | n/a | - | n/a | 3 |
| `probe-mutation:delayfix-seed419-r419bctlpos-b4095015-t2.json` | mutation:delayfix | program seed=419 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-mutation:delayfix-seed419-r419dctlpos-b3092030-t2.json` | mutation:delayfix | program seed=419 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-mutation:delayfix-seed420-r419cctlpos-b2091515-t2.json` | mutation:delayfix | program seed=420 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-mutation:hardcode-seed20260913.json` | mutation:hardcode | program seed=20260913 | 3 | 0/3=0.0000 | 0.0625 | {"partial": 2, "wrong_output": 1} | 非饱和 | n/a | n/a | - | n/a | 3 |
| `probe-mutation:nofix-seed419-r419bctlneg-b09141437-t2.json` | mutation:nofix | program seed=419 | 3 | 0/3=0.0000 | 0.3889 | {"wrong_output": 1, "partial": 2} | 非饱和 | n/a | n/a | - | n/a | 3 |
| `probe-mutation:nofix-seed419-r419bctlneg-b4095015-t2.json` | mutation:nofix | program seed=419 | 6 | 0/6=0.0000 | 0.5140 | {"wrong_output": 1, "partial": 5} | 非饱和 | n/a | n/a | - | n/a | 6 |
| `probe-mutation:nofix-seed419-r419dctlneg-b3092030-t2.json` | mutation:nofix | program seed=419 | 6 | 0/6=0.0000 | 0.5140 | {"wrong_output": 1, "partial": 5} | 非饱和 | n/a | n/a | - | n/a | 6 |
| `probe-mutation:nofix-seed420-r419cctlneg-b2091515-t2.json` | mutation:nofix | program seed=420 | 6 | 0/6=0.0000 | 0.2857 | {"partial": 3, "wrong_output": 3} | 非饱和 | n/a | n/a | - | n/a | 6 |
| `probe-oracle-seed20260913.json` | oracle | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | n/a | n/a | - | n/a | 6 |
| `probe-oracle-seed20260915.json` | oracle | program seed=20260915 | 3 | 3/3=1.0000 | 1.0000 | {"ok": 3} | **饱和** | n/a | n/a | - | n/a | 3 |
| `probe-r417-agent-seed20260913.json` | agent | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | 6413.8 | 6413.8 | 1 | 3072 | 0 |
| `probe-r417-hard-agent.json` | agent | program seed=20260914 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** | 8737.0 | 8737.0 | 1 | 18304 | 4 |
| `probe-r417-json-agent.json` | agent | program seed=20260915 | 3 | 0/3=0.0000 | 0.5000 | {"wrong_output": 1, "runtime_error": 1, "partial": 1} | 非饱和 | n/a | n/a | - | n/a | 3 |
| `probe-r417-json-mut.json` | mutation:json_loose | program seed=20260915 | 4 | 0/4=0.0000 | 0.7500 | {"partial": 4} | 非饱和 | n/a | n/a | - | n/a | 4 |
| `probe-r417-json-oracle.json` | oracle | program seed=20260915 | 2 | 2/2=1.0000 | 1.0000 | {"ok": 2} | **饱和** | n/a | n/a | - | n/a | 2 |
| `probe-r417-json-regrade.json` | file:/tmp/r417-replay | both seed=0 | 3 | 1/3=0.3333 | 0.8704 | {"partial": 2, "ok": 1} | 非饱和 | n/a | n/a | - | n/a | 3 |
| `probe-r417-mut-topodfs.json` | mutation:topo_dfs | program seed=20260914 | 4 | 0/4=0.0000 | 0.4615 | {"partial": 4} | 非饱和 | n/a | n/a | - | n/a | 4 |
| `probe-r417-mut-vmnoerr.json` | mutation:vm_noerr | program seed=20260914 | 4 | 0/4=0.0000 | 0.6042 | {"timeout": 2, "runtime_error": 2} | 非饱和 | n/a | n/a | - | n/a | 4 |
| `probe-r417-new-oracle.json` | oracle | program seed=20260914 | 4 | 4/4=1.0000 | 1.0000 | {"ok": 4} | **饱和** | n/a | n/a | - | n/a | 4 |
| `probe-r418-agent.json` | agent | program seed=20260916 | 3 | 2/3=0.6667 | 0.9811 | {"ok": 2, "partial": 1} | 非饱和 | 9151.0 | 9189.0 | 1 | 77699 | 0 |
| `probe-r418-json-mut.json` | mutation:json_loose | program seed=20260916 | 4 | 0/4=0.0000 | 0.7324 | {"partial": 4} | 非饱和 | n/a | n/a | - | n/a | 4 |

过程列（R418）: `tokens/题` = prompt 侧均值（**无 completionTokens**）；`turn≤` > 1 ⇒ 该题发生追问，属成本异常，须可见；
`n/a` = 归档回复缺失或**不可归属**（旧批次回复名无命名空间 ⇒ 跨轮同名覆盖，不猜）。n/a **不计入均值分母**，也不当 0。

## 4. 轮次提交（本地；推送暂停令生效）

- 未推送提交数: **86**

| commit | 主题 |
|---|---|
| `b1b5361` | digest: R428 重建 (137 行, ahead=85) |
| `52c5622` | R428: 同文折叠 (排序/去重层) —— R427 根因判定的产品落地 |
| `e0b9058` | R428-hold: 循环入口探针 v3 — 计划项行 (expN) 入账 + 自陈欠项判 open; 自检 15/15 (11 判定 + 4 负控); open 2→8, mode 恒 tasks; 零产品源码改动/零 dotnet/不占轮号 (R428 由 30m 节拍作业占用中) |
| `974cac7` | R426: 关系判官(CorrectionDetector L2)本地化 — 跳过轮残留远端微调用 4→1; A→C token k6 -67.6%/k8 -81.0%; 判据 PASS12/PARTIAL2/FAIL2/UNDECIDABLE1; k8 门判翻转反例登记; AOT IL 警告0 + 单测23/23 |
| `a1e9d3b` | R427 修复: improvements 追加节行结构破坏修复 + 行结构检测器 (共享文档一等事件) |
| `5227cdc` | R427: 「并列」根因判定——真实并列对为同文重复 + R423 闭式基线口径复核 (预检 PREMISE-REFUTED, 零产品改动) |
| `e8ada93` | R425: 前置门增益的占比敏感性网格 (判决 PARTIAL, 零产品改动) |
| `f4143b4` | R424 收口: 状态 digest 重生成(registry 59 行 updated_round R424; kpi 已记轮次含 R424; 未推送 78) (未推) |
| `560fb9c` | R424 主线 KPI 发布形态身份修复: R413 宣称 AOT 而器具跑 IL apphost(78,256B, env -i rc=131) ⇒ 在可自证 AOT 产物(15,168,064B sha 2d363b6d IL警告0)上三臂复现同一判据: A 12/16,888 → B 8/7,007 (-33.3%/-58.5% 均≥30%), 与 R413 JIT 读数逐位相同; 新增 B′(门开·模型缺=无设备负控兼 r1 归因: 12/16,891 ≡ A ⇒ 增益归零 ⇒ 归因 r1 非机械门); 形态闸 V0(env -i 自证+IL 成对负控)/门真身 V1/无效跑 V2 全绿, 判据 9 预注册+5 事后(P1 回复逐字节无回归 / P2 role 额外数据真挂载: IndustrialAgentV2.cs:1481 ProfileSeed 非空 / P3 无设备失败可见性 4/4) PASS; r413 器具 fail-closed 封堵(rc=2) + 更正登记; 轮号碰撞让号至 R424(对侧 R423=检索 tf); 回归抽查 47/47 (未推) |
| `1046899` | R423 证据补齐: 命名空间碰撞的轮内消解入档(对侧让号至 R424, 迁移 17:10:36) — 台账 namespace_collision 字段 + 计划 §11 + 证据 §7 (未推) |
| `a2d6416` | R423 收口: 状态 digest 重生成(未推送 75 / registry 58 行+updated_round R423 / R423=检索打分) + 生成器增「轮号命名空间」纪律行(碰撞登记: 并发执行体让号至 R424; 提交禁 git add -A) (未推) |
| `e57be12` | R423 跨会话检索打分词元频次饱和: 可分性预检(残留并列对 distinct 90/90 ∧ tf 4/4 逐项相等 ⇒ 词袋计数族不可分边界登记, 不作全称宣称) + 打分子 1+ln(tf)(因子≥1 ⇒ 命中集合可证不变) + 真机成对AOT两臂(等长对 [0.4901×2] 全等 → [1.0286,0.4901] 分档, 比值==1+ln3) + 冻结语料 tf=1 逐位不变/tf=4 ==登记值×(1+ln4) + 单测26/26 + 形式校验13/13; 另: 首跑预测输入纠错与语料目录污染两起事故入档 + 命名空间碰撞登记(对侧R423=AOT形态复现, 其产物未动) (未推) |
| `c8c4652` | R422 跨会话检索打分校准(文档长度归一) + 附带修复词袋 embedding 溢出/随机哈希 |
| `37d6997` | R421 跨会话检索否定极性: 否定标记(不没未无五)紧邻词元带极性问题(¬存在≠存在) ⇒ `/recall 不存在` 3命中→0 |
| `7d3165b` | R420 L2-待办①/L7-G1 跨会话检索接线: /recall 本地指令(四表同步, 零LLM, recall_query 通道级打点) + 接线前产物负控(recall_query=0/llm_call=1) + 单测28/28 + 表单13/13; 真机暴露否定无感假阳性(下轮候选, 未修) (未推) |
| `05b8c94` | R419 收口: 探针多轮化仪器达成 + 真机读数未稳定分化(3/4 饱和) + 三个仪器缺陷修(坏字节崩/NS覆盖/可见性) |
| `98339a8` | R419 §4/§5: 探针多轮化落地 + 成对控制 + 真机复数（预注册判据反向红） |
| `77a49bc` | R419: 会话续跑决定性微实验 PASS(同 sid 跨进程 4271 命中) + 口径坑记录(turn N 是进程内轮次, 轮数须取归档文件数) (未推) |
| `695d6ba` | R419 起步存档: 探针多轮化立案(轮数/首次通过率从恒等变可分化) + 决定性微实验待跑 (未推) |
| `1f44c8b` | R418 探针「过程/成本」维度 KPI: 归属铁律 + 真机成本读数 + 成对负控 |
| `737a45d` | R418 起步存档: 探针过程/成本维度KPI 侦察事实+设计+待办 (上下文压缩点恢复指针, 未推) |
| `0488017` | R417 探针反饱和: 3 个高判别力族(topo_min/vm_run/json_mini)+tight_gen 强制规格紧用例+族级缺陷注入负控(正负控成对); 同题复跑确认饱和; 真机仍饱和如实登记; digest 增探针分数段(含饱和标记) |
| `f36f897` | R416 收工记录: improvements 轮节 + backlog 看板 D2 证据指针 (形式校验 13/13 PASS, 未推) |
| `2b831ac` | R416 能力自检循环: R371-D2 发布产物自包含 config 仓库外真机验收 (3 臂/6 断言 PASS) |
| `e53f8c5` | chore: R415 臂执行脚本与本地提交脚本入库 + r413 裸日志入 .gitignore |

## 5. 台账

- `docs/verification-registry.json`: **63** 行, updated_round = **R429**
- `eval/capability/kpi.jsonl` 已记轮次: R402, loop-mechanism, R401, R411-V, R403-scope, R413, R414, R415, R416, R419, R420, R421, R422, R423, R424, R425, R427, R428, R428-hold, R429
- 已知盲区: 状态检测器只读 `data/probe/kpi.jsonl`; 轮次台账另有 `data/probe/capability/kpi.jsonl`（孤儿）
- **轮号命名空间（R423 实证，轮内已消解）**: 轮号取 `max+1` 前必须复跑「pgrep 活动执行体 + 锁文件 + 目标轮文件存在时比对 mtime（>10min 才算 stale）」全序列。R423 曾与并发执行体撞号（本侧=检索打分；对侧=AOT 发布形态复现），对侧随后**让号**至 R424（`eval/rover/r424/` + `docs/plans/v0.45.0-r424-aot-mainline-replication.md`）⇒ 最终 R423=检索打分 / R424=AOT 形态复现。**处置纪律**: 碰撞当一等事件（两支都登记、不改写历史、不静默改名）；提交只用**显式路径**（禁 `git add -A`，防卷入对侧未跟踪产物）。

## 6. 口径红线（审计对照）

1. AOT 是唯一发布形态; JIT 跑通只算中间证据 (IL 警告必须为 0)。
2. 测量取**外部真值**: 桩/假后端逐请求落盘, 不信被测量代码自报计数器。
3. 计数口径 tokens_evaluated = 总长, prompt_n = 新算, cache_n = 命中 (恒等; 错算 ⇒ 比率 > 1)。
4. llm_call.truncated 是**最终**闭合性 (救回后为 false); 截断事实只在 llm_call_continue。
5. 「没测到」≠「失败」; 负控必须实测为 0, 缺正控时「仪器错」与「被测错」不可分。
6. 写源码的尖括号字面量会被工具替换 ⇒ 用转义/字符码构造常量, 写后按码点复核。
7. 推送暂停令未解除 ⇒ 只本地 commit; 凭据一律不入 git config、不硬编码。

## 7. 复验命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release
"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_release
python3 scripts/dev_return_digest.py   # 重新生成本文件
```
