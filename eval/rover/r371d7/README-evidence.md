# R371-D7/D1 真机验收 + R414 失败可见性修复 · 证据清单

> 判据先于测量；**计数取外部真值**（桩 `stub_arm.py` 逐请求落盘 + 驱动器观测），被测量代码自报遥测只作交叉核对。
> 结算器：`python3 verdict.py` → `verdict-r371d7.json`（4 臂 / 24 项断言 / **PASS**）。

## 1. 怎么跑（复现）

```bash
# 需要: 已构建的宿主 (src/agent.host/bin/Release/net10.0/agenthost)
cd /home/agentuser/AgentFramework
for A in ok truncate empty empty_always; do bash eval/rover/r371d7/run_arm.sh $A 47830 47831; done
python3 eval/rover/r371d7/verdict.py
# 单测 (修复判据)
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release --filter FullyQualifiedName~UserFacingFailureTests
```

## 2. 文件

| 文件 | 作用 |
|---|---|
| `stub_arm.py` | 确定性远端桩（`ok`/`truncate`/`empty`/`empty_always`）；**逐请求落盘 `calls-<arm>.jsonl`**（seq/messages/nudge 命中/prompt_est/`resp_content`/`resp_reasoning_len`/`finish_reason`） |
| `drive_d7.py` | 真链驱动器（`agenthost --frontend-api`，首行 auth，`chat.send`，逐轮记录 ok/secs/reply_len/success/events） |
| `task.json` | 2 轮任务（1: 写求和函数；2: 复述结论） |
| `run_arm.sh` | 单臂执行：独立 cwd + 独立 master.key + 独立 config（stub 地址）+ 收尾杀进程（按 pid，不用 `pkill -f`） |
| `verdict.py` | 结算器（含**独立复刻**的截断判据 + 合并长度） |
| `calls-*.jsonl` / `turns-*.jsonl` / `tel-*.jsonl` | 桩侧请求 / 用户可见轮次 / 宿主遥测（**外部真值优先**） |
| `turns-before-fix-empty_always.jsonl` | **修复前对照**（轮 1 `reply_len=0`） |
| `verdict-r371d7.json` | 结算结果（PASS + 每项实测值） |
| `publish_aot.sh` | R414 收尾 AOT 重发布（0 IL 警告核对） |

## 3. 读数

### 3.1 修复后（本轮产物 = 提交内容）
| 臂 | 远端请求 | 关键读数 |
|---|---|---|
| `ok` | 2 | 恢复遥测 0 / `truncated=true` 0 / 回复 `reply_len=[37,44]`（**负控：无病不治**） |
| `truncate` | 4 | `llm_call_continue before=102 added=58 after=144 recovered=true`；`after`=独立复刻 144（overlap=16）；`tail_before`=桩侧断点原文；救回后 `truncated=false`；可见回复含 `return acc` 且结构闭合 |
| `empty` | 4 | `llm_call_recover first_content_len=0 first_reasoning_len=400 recovered=true`；回复 `reply_len=[37,44]`（正文） |
| `empty_always` | 4 | `recovered=false`（如实不救回）；`success=[False,False]`；**可见降级文案 `reply_len=[66,73]`** |

### 3.2 修复前对照（同一 harness，旧二进制）
`empty_always` ⇒ `reply_len=[0,73]`：轮 1 **空白**（`loop_turn success=false reply_chars=0`）⇒ 该臂第 5 项断言在修复前必失败（**探针判别力实证**）。
其余三臂修复前后逐位一致（零回归）。

### 3.3 AOT 发布形态复跑（`FORM=aot`，`AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r414/agenthost`）
| 臂 | 桩侧请求（外部真值） | 可见回复 |
|---|---|---|
| `empty_always` | 4 请求 / 带抑制推理提示 **2** | `reply_len=[66,73]` ∧ `success=[False,False]`（修复在 AOT 形态生效） |
| `truncate` | 4 请求 / 带续写提示 **2** | `reply_len=[144,151]` ∧ `success=[True,True]`（D7 在 AOT 形态生效） |

> 证据文件带 `-aot` 后缀（`calls-*-aot.jsonl` / `turns-*-aot.jsonl` / `tel-*-aot.jsonl`），不覆盖 JIT 读数。
> `run_arm.sh` 第 4 参 = 形态（`jit`|`aot`）；`AGENTFRAMEWORK_HOST_BIN` 可指定被测二进制。

## 4. 口径澄清（审计须知，非缺陷）

1. `llm_call.truncated` 记录的是**最终**正文闭合性 ⇒ D7 救回后为 `false`；「首轮被截断」的事实只在 `llm_call_continue.before_len/tail_before`。**只看该字段会漏掉已救回轮。**
2. `llm_call_continue.added_len` = **续写原文长度（去重前）**；增量 = `after_len - before_len = added_len - overlap`。两者不可混用。
3. 遥测路径：`run-<arm>/data/telemetry/host.jsonl`（已复制为 `tel-<arm>.jsonl`）。

## 5. 诚实边界

1. 桩驱动 ⇒ 证明**机制**（触发/续写/去重/透出/裁决），**不是**自然分布下的截断率或失败率。
2. `empty_always` 是**构造的病态分布**（人工 100% 空正文），真实 provider 下该分支罕见。
3. 单机 / 单模型配置 / 单次读数；含本机既定参数（`AGENTFRAMEWORK_CONFIG` 覆写、无本地通道）。
4. 修复语义：失败**仍然是失败**（`Success=false` 不变），只是不再静默——不构成「修好了模型输出」。
