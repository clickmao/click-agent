# R433 证据 —— 文档跑测链复位 + 取码产物通道（假红裁决）

**轮号**: R433 · **日期**: 2026-09-14 · **被测二进制**: `/tmp/pub_r433/agenthost`（HEAD 发布, IL 告警 0, sha256 `a2b3f421…`, 15,184,624 B）
**题集**: 冻结 `data/probe/taskset-m6.json` sha `b8e796a6d803918d`（严格同题）

## 0. 为什么这一轮是这个靶点（用户纠偏令, 逐字）

> 「进行下轮，但是请你仔细审查有没有偏离主题，我感觉你越来越精细，却一直没怎么严格执行文档中的跑测计划，不看数据只开发是不行的」

**机检偏离审查**（读数先于解释）:

| # | 文档要求（源） | 机检 | 实测 | 判定 |
|---|---|---|---|---|
| A1 | 打点: run 摘要 → `kpi_probe` → `data/probe/kpi.jsonl`（`eval/probe/README.md` §运行） | 行数 + 末行 ts | 6 行, 末行 `2026-09-13T23:20` | **停摆 ~21h** |
| A2 | 摘要与台账应一一对应 | `data/probe/probe-*.json` = 30 份（最新 09-14 15:44） vs sink 6 行 | 24 份**未打点** | **链断在第二段** |
| A3 | exp14 M6「扩族 + 常态化」 | `docs/plans/v0.24.0-exp14-random-probe-selfcheck.md` | 状态 ⏳ 待做 | 未执行 |
| A4 | 近 8 轮（R424–R432）产出落点 | `git log` + `eval/capability/kpi.jsonl` | 读数只进 `eval/capability/kpi.jsonl`; **0 行进 KPI sink** | **偏离实锤** |

⇒ 结论: 预算全投入「判定器/门判仪器精细化」，**没有一轮产生文档 KPI 链的新读数**。本轮 = 严格执行文档跑测链并看数据。

## 1. 因果链

1. 按 `eval/probe/README.md` 逐步执行: 5 套 selftest → AOT 发布 → 真机 agent 臂（同题）→ 负控臂 → `process_metrics` → `kpi_probe` 打点。
2. 同题 A/B（旧仪器）: 基线 09-13 `1.0000` → 本轮 **`0.6944`**（1 题 `syntax_error`）。
3. 复跑（旧仪器）: 仍 `0.6944`，但**换了一题**（run1 = p003, run2 = p002）⇒ 每 run 恰 1/3 程序题假红。
4. 根因取证（三通道）:
   - ① 归档回复 = **渲染后的 TUI 转录**（`｜ code_generation` 等装饰行 + `__name__` 被吃成 `name`），取码候选=1 且为装饰片段 ⇒ `SyntaxError: invalid character '｜' (U+FF5C)`；
   - ② 产品遥测 `script_artifact` **外部真值**: 3/3 程序题 `origin="fenced"`、`compile_valid=true`（源码本就正确且可编译）；
   - ③ 判定器自身: `candidates()` 只认「回复文本里的围栏 / 回复里的产物路径」，**不认遥测落盘产物** ⇒ 通道缺口。
5. 修（仅评估面 `eval/probe/*.py`）: 产物路径作为**外部真值通道**并入候选（`code_source` 可见）+ 归属用闭区间进程窗口（`[t0-0.25, t1+0.25]`）。
6. 修后真机同题: **`1.0000`（36/36）**，两次独立臂一致，归属 1 题 1 产物 ⇒ **旧读数是 100% 假红**。

## 2. 读数表（全部机检，非人工抄录）

| run | 仪器 | 题集 sha | 整题全对 | 用例级 | 结论 |
|---|---|---|---|---|---|
| `probe-m6-agent.json`（09-13 基线） | 旧 | b8e796a6d803 | 6/6 = 1.0000 | 1.0000 | 基线 |
| `probe-agent-seed0-r433m6.json` | 旧 | b8e796a6d803 | 5/6 = 0.8333 | 0.6944 | **假红**(p003) |
| `probe-agent-seed0-r433m6r2.json` | 旧 | b8e796a6d803 | 5/6 = 0.8333 | 0.6944 | **假红**(p002) |
| `probe-agent-seed0-r433m6fix.json` | 修后 | b8e796a6d803 | 6/6 = 1.0000 | 1.0000 | 无退化 |
| `probe-agent-seed0-r433m6fix2.json` | 修后 | b8e796a6d803 | 6/6 = 1.0000 | 1.0000 | 无退化（归属精确） |
| `probe-agent-seed20260913-r433as.json`（抗饱和族） | 修后 | f7b1a5320cdf | 3/3 = 1.0000 | 1.0000 | 新题集无退化信号 |
| `mutation:topo_dfs` / `vm_noerr` / `json_loose` | 本地 | — | **0/3 / 0/3 / 0/3** | 0.4359 / 0.6250 / 0.7037 | 判别力未饱和 |

成本（`process_metrics.py`，prompt 侧 only）: `tokens/题` = 台账首轮的 6021.8（旧仪器 run1）、6001.3（fix）、6032.7（fix2）；墙钟均 15108/20362/31652 ms。

## 3. 台账复位

`python3 scripts/kpi_probe.py --run … ×9 --compare probe-m6-agent.json seed0-r433m6fix2.json --report eval/capability/r433/kpi-report.md`
⇒ `data/probe/kpi.jsonl` **6 → 14 行**（+8），A/B 段判定「同批题集 ⇒ Δ 可比」，A/B 质量 Δ = +0.0000。

## 4. 诚实边界

1. **不宣称 token 变化**: 09-13 基线在遥测窗口外 ⇒ `tok/题 = n/a`（按口径记 n/a, 不记 0）; fix 臂间 tok/题 6.0k–9.2k 落在远端模型噪声带内。
2. run2 的假红只证明「同机制、同 mode、同转录病因」，其 p002 的产物判分未逐题留证（run1 的 p003 已逐题留证）。
3. 墙钟方差极大（同题 91.97 → 191.57 s）⇒ 墙钟不作能力判据。
4. **离线复放（读历史快照）归属不精确**（缺精确 t0，会过归属）⇒ 只作机制验证，**不采信为读数**；权威读数只取真机运行态。
5. 单机单次节拍；抗饱和族题集 sha 与 R417 不同（生成器已加硬）⇒ 该行非同题 A/B，只作「无退化信号」。
6. `code_source` 只在 `eval/probe` 台账可见；产品侧 `script_artifact` 遥测仍是唯一产物真值源。

## 5. 复现命令

```bash
export DOTNET_ROOT="$HOME/.dotnet"
"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r433
export PROBE_AGENT_BIN=/tmp/pub_r433/agenthost
python3 eval/probe/grade.py --selftest && python3 eval/probe/run_probe.py --selftest
python3 eval/probe/run_probe.py --tasks data/probe/taskset-m6.json --solver agent --tag=r433m6fix2
python3 eval/probe/process_metrics.py --glob 'data/probe/probe-*r433*.json' --report
python3 scripts/kpi_probe.py --run data/probe/probe-m6-agent.json --run data/probe/probe-agent-seed0-r433m6fix2.json --compare probe-m6-agent.json seed0-r433m6fix2.json --report eval/capability/r433/kpi-report.md
```

**形式校验（门禁）**: `/tmp/gate_r429.sh` = **12/13**（VerificationFormTests/DevPlanDocRefTests/SkillGeneralizationTests 13 例）。唯一红项 = **对侧 R431 行** `r431.gate-role-growth-mount` 的 `covers` 使用 `path:anchor` 形式（R2c 判路径不存在, 由 `f319198` 引入）⇒ 本侧不改他方产物, 仅登记（承 R432 的 `eval/rover/r432/PEER-GATE-RED.md`）；本侧 R433 行 67 `covers` 全为纯路径且逐个存在。
