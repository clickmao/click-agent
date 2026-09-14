# R413 证据清单（含**失效跑**如实入档）

判据口径：C1 远端调用 ↓≥30% · C2 总 token ↓≥30% · C3 负控=4 条实质轮(1/3/5/7)零误跳 · C4 跳过集=预注册寒暄集且回复=非 LLM 模板。
结算器：`python3 verdict.py`（只读桩侧逐请求落盘 + 驱动器观测）⇒ `verdict-r413.json`。

## 有效读数（判据所用）

| 文件 | 内容 |
|---|---|
| `budget-A.json` / `calls-A.jsonl` / `turns-A.jsonl` | 臂 A：本地通道**关**，12 调用 / 16,888 token |
| `budget-B.json` / `calls-B.jsonl` / `turns-B.jsonl` | 臂 B：前置门 v2 **开**，**8 调用 / 7,007 token（-33.3% calls / -58.5% token）** |
| `run-B/data/telemetry/host.jsonl` | 门遥测：`local_turn_gate_config`（门已开/role=skeptic）+ 7 条 `local_turn_gate`（机械 Pass 3 + r1 Skip 4） |
| `probe-struct.jsonl`(+`.summary.txt`) | 单组件探针：5 种出参格式 × 6 条（V1 二元 S/P 6/6 合法；V2 JSON 4/6 且 kind 判错；V3/V4 prefill 1/6 不生效；V5 24-tok 假合法） |
| `baseline-breakdown.json` | 臂 A 拆分：真假判别 139 / 11,025 token = 1.26%（⇒ 30% 必须靠主调用前置过滤，不能靠判别本身） |

## 失效跑（如实保留，**不作判据**）

| 文件 | 为什么失效 |
|---|---|
| `armB-v3-invalid.log`（**logs 被 .gitignore 排除 ⇒ 原文内联在此**） | 臂 B **第一次**真机跑：12 调用 / 16,888 token，与臂 A **逐位相同**（增益 = 0）。根因 = 门判的是 `prompt.UserMessage`（该字段已被追加 role 块/计划续跑/微提示）⇒ 机械门**恒 Pass**、增益归零；修法 = 改判 `message.Content`（用户本轮原文）+ G29 源级回归钉死。此跑是**空心诊断的决定性证据**，故入档而非丢弃。 |

v3 失效跑原文（判据不用；指纹 = 每轮 <0.8s ⇒ 本地 r1 从未启动 ⇒ 门恒 Pass）：

```
[config] arm=B 改写了 4 处 request_address → 桩 :47820; local 段=有
[ready] api :47810 (2s)
[turn 1] ok=True secs=0.76 reply_len=15      ← reply_len=15 = 桩的罐头应答, 不是模板
[turn 2] ok=True secs=0.06 reply_len=15
[turn 3] ok=True secs=0.05 reply_len=15
[turn 4] ok=True secs=0.05 reply_len=15
[turn 5] ok=True secs=0.08 reply_len=15
[turn 6] ok=True secs=0.12 reply_len=15
[turn 7] ok=True secs=0.01 reply_len=168
[turn 8] ok=True secs=0.09 reply_len=15
{"stats": {"turns": 8, "ok": 8, "events": 23, "asks": 4, "errors": []}}
[budget] {"arm": "B", "remote_calls": 12, "prompt_tokens_est": 16804, "completion_tokens_est": 84, "total_tokens_est": 16888}
```

对照 v4 有效跑（`turns-B.jsonl`）：轮 2/4/6/8 = **10.6–17.7s**（走了本地 r1 判别）且 `reply_len=21` = 模板原文；轮 1/3/5 <0.8s（机械 Pass ⇒ 远端）。**秒数 + reply_len 两项即可在外部区分「门消化」与「过 LLM」**。

## 复现

```bash
bash run_arm.sh A 47820 47810 /abs/path/skeptic.rbin   # 臂 A（无 local 段）
bash run_arm.sh B 47820 47811 /abs/path/skeptic.rbin   # 臂 B（附加 local 段: turn_gate 开）
python3 verdict.py                                      # 结算 → verdict-r413.json
bash publish_aot.sh                                     # AOT 重发布 + IL 警告计数
```
脚本每次运行会清空并重建 `config-{A,B}/`、`run-{A,B}/`、`calls-*.jsonl`；`run-*/data/master.key` 为测试用临时密钥，**不入库**。
