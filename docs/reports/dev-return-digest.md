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

## 2. 探针裁决（源: `eval/rover/*/verdict*.json`）

| 目录 | 裁决文件 | verdict | 判据数 | 来源键 |
|---|---|---|---|---|
| r371d2 | verdict-r371d2.json | **pass** | 6 | `assertions` |
| r371d7 | verdict-r371d7.json | **PASS** | 5 | `arms` |
| r412 | verdict.json | **NO_CONTENTION** | 4 | `bool_fields` |
| r413 | verdict-r413.json | **PASS** | 7 | `gate` |
| r415 | verdict-r415.json | **PASS** | 22 | `checks` |

**正文提及但无独立小节的 D 编号**（文档缺口, 不猜测其状态）: D6(L237), D9-a(L182)

## 3. 探针分数（质量；源: `data/probe/probe-*.json`）

打分单元 = **整题全对**（该题全部隐藏用例通过才算过）；`rate` 为用例级率（旁读）。
**饱和** = 整题全对 ∧ 用例级率均为 1.0 ⇒ 该题集对本解法已到天花板，**不能再用于度量质量**（需换更难族）。

| 文件 | 解法 | 题集 | 题数 | 整题全对 | rate(用例级) | 失败模式 | 判定 |
|---|---|---|---|---|---|---|---|
| `probe-agent-seed20260913.json` | agent | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-m6-agent.json` | agent | both seed=0 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-m6-hardcode.json` | mutation:hardcode | program seed=20260913 | 3 | 0/3=0.0000 | 0.1818 | {"partial": 3} | 非饱和 |
| `probe-m6-oracle.json` | oracle | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-mutation:hardcode-seed20260913.json` | mutation:hardcode | program seed=20260913 | 3 | 0/3=0.0000 | 0.0625 | {"partial": 2, "wrong_output": 1} | 非饱和 |
| `probe-oracle-seed20260913.json` | oracle | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-oracle-seed20260915.json` | oracle | program seed=20260915 | 3 | 3/3=1.0000 | 1.0000 | {"ok": 3} | **饱和** |
| `probe-r417-agent-seed20260913.json` | agent | both seed=20260913 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-r417-hard-agent.json` | agent | program seed=20260914 | 6 | 6/6=1.0000 | 1.0000 | {"ok": 6} | **饱和** |
| `probe-r417-json-agent.json` | agent | program seed=20260915 | 3 | 0/3=0.0000 | 0.5000 | {"wrong_output": 1, "runtime_error": 1, "partial": 1} | 非饱和 |
| `probe-r417-json-mut.json` | mutation:json_loose | program seed=20260915 | 4 | 0/4=0.0000 | 0.7500 | {"partial": 4} | 非饱和 |
| `probe-r417-json-oracle.json` | oracle | program seed=20260915 | 2 | 2/2=1.0000 | 1.0000 | {"ok": 2} | **饱和** |
| `probe-r417-json-regrade.json` | file:/tmp/r417-replay | both seed=0 | 3 | 1/3=0.3333 | 0.8704 | {"partial": 2, "ok": 1} | 非饱和 |
| `probe-r417-mut-topodfs.json` | mutation:topo_dfs | program seed=20260914 | 4 | 0/4=0.0000 | 0.4615 | {"partial": 4} | 非饱和 |
| `probe-r417-mut-vmnoerr.json` | mutation:vm_noerr | program seed=20260914 | 4 | 0/4=0.0000 | 0.6042 | {"timeout": 2, "runtime_error": 2} | 非饱和 |
| `probe-r417-new-oracle.json` | oracle | program seed=20260914 | 4 | 4/4=1.0000 | 1.0000 | {"ok": 4} | **饱和** |

## 4. 轮次提交（本地；推送暂停令生效）

- 未推送提交数: **64**

| commit | 主题 |
|---|---|
| `f36f897` | R416 收工记录: improvements 轮节 + backlog 看板 D2 证据指针 (形式校验 13/13 PASS, 未推) |
| `2b831ac` | R416 能力自检循环: R371-D2 发布产物自包含 config 仓库外真机验收 (3 臂/6 断言 PASS) |
| `e53f8c5` | chore: R415 臂执行脚本与本地提交脚本入库 + r413 裸日志入 .gitignore |
| `5ac3b43` | R415: 链级钉死前置门入参=用户原文(真链+确定性假本地后端, 22断言x2形态 PASS) + 仪器两项教训入档 |
| `5fc876f` | R414: R371 断链真机验收(D7 优先) + 失败可见性缺陷闭合(Success=false 的降级文案不再被链侧丢弃) |
| `f6496ba` | R413 证据补齐: 失效跑(v3 门恒Pass/增益0)原文入档 + 证据清单(有效/失效分列) + 本地提交脚本 |
| `c400b45` | R413: r1 本地真假判别接进链管道(端口化) + 机械 Pass 前置 + 非 LLM 模板 ack |
| `b29e450` | R403 报告 §9: 附带发现(三台账/检测器视图缺口 + 主报告 §7 快照滞后), 交下轮裁定 |
| `cd3c951` | R403: chat template 裁定 —— 工具调用模板无对象可验(负控证明探针有判别力), R403 关闭 + 待触发能力准入三条 |
| `19aff03` | R412: 多会话 slot 争用实测 + 会话级账本(分母不互相污染) |
| `6a7a519` | R411: 通用教训落 skills/delivery-selfcheck (7b 字段语义核查 + 走偏表两行) |
| `20bf988` | R411: 长驻生成端口 + 本地 K2b 台账(双条件判据) + 口径独立对账钉死 |
| `6483721` | R411-V: 登记表可执行性机检(R2b/R2c/R2d) + 9 行死引用纠偏 + 退役能力降级收口 + R402 步2 读数补登记(加线程不升级) |
| `612075b` | R410 (2/2): 文档/登记 + 会话长前缀入口 + 两个墙钟假红缺陷修复 |
| `8263ac8` | R410 (1/2): 生成口径分离(对账 vs 会话) + K2b 前缀复用记账 |
| `46e0f37` | R409: 通用教训落 skills/delivery-selfcheck (步骤7 口径核查 + 走偏表三行) |
| `7bb06fa` | R409: 本地 prompt 模板闸门(结构性阻断手拼) + 权威 prompt BOS 口径修正 |
| `b00917c` | R408: 本地 GGUF 引擎整线退役, 本地推理/嵌入改走 llama.cpp 进程边界 (零 P/Invoke) |
| `3b20986` | R401 步2: rover 臂测量链三缺陷归因+修复(渲染/臂可用性/预算协同) + 跨实现字节对账 2/2 + 校准常数实测; 新技能 self-verification-blindspots |
| `cd8feeb` | R407: qwen2 前向对账 —— 定位并修复「全层共用 blk.0 attn bias」(R403–R407 工作区一并提交) |

## 5. 台账

- `docs/verification-registry.json`: **52** 行, updated_round = **R417**
- `eval/capability/kpi.jsonl` 已记轮次: R402, loop-mechanism, R401, R411-V, R403-scope, R413, R414, R415, R416
- 已知盲区: 状态检测器只读 `data/probe/kpi.jsonl`; 轮次台账另有 `data/probe/capability/kpi.jsonl`（孤儿）

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
