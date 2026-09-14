# R418 证据 · 探针「过程/成本」维度 KPI

复现：`bash eval/rover/r418/run1_process_kpi.sh`（仪器自检 → 真机 1 臂 → 成对负控 → 成本表，约 5 min，日志 `/tmp/r418-proc.log`）。

## 0. 仪器自检（[0] 段）

| 仪器 | 结果 |
|---|---|
| `eval/probe/process_metrics.py --selftest` | **14/14**（本节新增仪器） |
| `eval/probe/grade.py --selftest` | 29/29 |
| `eval/probe/run_probe.py --selftest` | 18/18 |

## 1. 真机臂（[A] 段，AOT `PROBE_AGENT_BIN=/tmp/pub_r414/agenthost`）

`json_mini`，`--n 3 --kind program --seed 20260916` ⇒ `data/probe/probe-r418-agent.json`

| tid | 结果 | 用例级 | prompt tokens | 墙钟 ms | turns |
|---|---|---|---|---|---|
| p001 | ok | 17/17 | 9322 | 45997 | 1 |
| p002 | **partial** | 17/18 | — | — | 1 |
| p003 | ok | 18/18 | — | — | 1 |
| **合计** | **整题全对 2/3 = 0.6667** | **52/53 = 0.9811** | **Σ27453 → 9151/题** | **均 77699（77.7 s/题）** | **≤1** |

- 唯一失分 = p002 **case#3**：`got '["a\tb"]'` / `want 'ERR'`（含**裸 TAB** 的字符串必须判非法），与 R417 同一处紧用例。
  **双路径核对**（活跑 + 离线复判同一题集，`python3 eval/rover/r418/verify_p002_failure.py`）：逐题 17/17 · 17/18 · 18/18 = 52/53，与活跑**逐位一致** ⇒ 用例级 0.98 而整题全对仅 2/3，再次印证「**判分单元必须是整题全对**」。
- 口径字段：`llmModel=deepseek-flash`；`na_count=0`、`malformed_fields=0`、`ambiguous_replies=0`；`reply_ns=s20260916`。

## 2. 成对负控（[B] 段）

`mutation:json_loose`，同题集同 seed n=4 ⇒ `data/probe/probe-r418-json-mut.json`

- 整题全对 **0/4**、用例级 52/71 = 0.7324 ⇒ **判别力仍在**（与 R417 一致）。
- 该臂**不走 LLM** ⇒ 过程指标 **4×n/a**；报告**不记 0**（记 0 会伪造「零成本」假象）。

## 3. 归属证据（[D] 段）

```
agents20260916-p001.txt 12727 B  13:40
agents20260916-p002.txt 10965 B  13:42
agents20260916-p003.txt 14865 B  13:44
mutation_json_looses20260916-p001..p004.txt （各 216 B）
```

命名空间（`--tag` 或 seed）生效 ⇒ 下游可**确定性归属**（`source` 字段指向具体文件，`note=ns_exact`）。

## 4. 成本表（[C] 段，`data/probe/process-metrics-r418.json`）

| 题集 | 题数 | 整题全对 | 用例级 | 首次通过率 | tokens/题 | tokens/满分题 | 墙钟均(ms) | turn≤ | n/a | 畸形 |
|---|---|---|---|---|---|---|---|---|---|---|
| `probe-r418-agent.json` (agent) | 3 | 2/3=0.6667 | 0.9811 | 2/3=0.6667 | 9151.0 | 9189.0 | 77699 | 1 | 0 | 0 |
| `probe-r418-json-mut.json` (mutation:json_loose) | 4 | 0/4=0.0000 | 0.7324 | 0/4=0.0000 | n/a | n/a | n/a | - | 4 | 0 |

## 6. 收尾门（`bash eval/rover/r418/gates.sh`，日志 `/tmp/r418-gates.log`）

| 门 | 结果 |
|---|---|
| `tasks.py --selftest` | 45/45 |
| `grade.py --selftest` | 29/29 |
| `run_probe.py --selftest` | 18/18 |
| `process_metrics.py --selftest` | **14/14** |
| `eval/kpi/kpi_probe.py --selftest` | PASS |
| 形式校验（`VerificationFormTests`） | **6/6** |
| 全量单测 | **1164/0/0**（30 s） |

- **全量跑的前两次各 1 例假红**（`TelemetryPendingTests`、`ModelQueueTests.Router_Consecutive_Failures_Switch_With_Audit`，**受害者不同**），各自**隔离复跑即绿**（2/2、10/10）。清理 4 个上一轮残留的 `llama-server`（bge×3 + r1×1，共 ~135 MB）后第三次跑 **1164/0/0** ⇒ 判为**同机争用假红**（与 R417 同一模式，如实记录）。
- **登记表校验器抓到我自己的坏行**：`r418` 行初版把 6 个证据文件写进 `evidence_path`（`;` 拼接）⇒ `R2` 判「不存在」⇒ 红；修 = `evidence_path` 单路径 + 其余入 `covers`。**这是校验器有效性的一次正面证据**（`VerificationFormTests` 6/6 通过后写入）。
- **副产物已还原**：`eval/kpi/kpi_probe.py --selftest` 会重写 `eval/results/kpi_r369.json`（R369 旧读数重算），本轮**未采纳**（回滚，避免把未评估的重算数据混入提交）；`eval/bge/r404/csharp-fusion-replay.json` 同类。
- **原始证据不入 git**：`data/` 在 `.gitignore` 内 ⇒ 探针 JSON / 归档回复 / 成本表**只在本机**，仓库内证据 = 本文件 + `eval/rover/r418/` 脚本 + registry 行（`r418.probe-process-kpi`，L4）。

## 7. 诚实边界

1. **只有 prompt 侧 + 墙钟**：链不落 `completionTokens`（`data/probe/replies/*.txt` 实测无该字段）⇒ 报总成本会**低估**。
2. **探针单轮**：`turns` 恒 1 ⇒ 目前主要作**异常检测**；「首次通过率」与「整题全对率」同分母（真正区分需链路出现重试/追问）。
3. **旧批次不回填**：R413–R417 归档无命名空间 ⇒ 成本**一律 n/a**（修窗前实测 3 份 run 会读到同一批回复 = 张冠李戴；修窗后 `ambiguous=0`、`na_sum=61` 全部如实标 n/a）。
4. **n=3 小样本**，只作机制证据，不作分布结论。
5. 本轮**未改产品代码** ⇒ 无需重发 AOT（`/tmp/pub_r414` 即 R414 的 IL 0 产物）。
