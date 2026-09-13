# eval/probe — 随机化能力自检探针（exp14）

> 长期任务：用**随机程序题**与**随机数学题**给本 agent 做能力自检，并把经验抽象成**语言无关的通用性 skill** 落 `skills/`。
> 计划：`docs/plans/v0.24.0-exp14-random-probe-selfcheck.md`

## 文件

| 文件 | 行数 | 作用 |
|---|---|---|
| `tasks.py` | 627 | 随机题集生成器：程序 6 族 + 数学 5 族；**每答双路径验算**，不一致则拒绝发题；`--selftest` 21 条负控 |
| `grade.py` | 300 | 判定器：沙箱执行 + 隐藏用例比对 + **失败模式分类** + 判定器自身反向负控；`--selftest` 13 条 |
| `run_probe.py` | 380 | 编排器：题集 → 适配器 → 判定 → 结构化摘要；`--selftest` 11 条 |

## 判分口径（三条铁律）

1. **只认隐藏用例**：公开样例只用于题面，从不参与判分。
2. **整题全对才算过**：用例级通过率会给出作弊空间（实测：硬编码公开样例的解仍能拿 22.2% 用例通过率）。
3. **失败必须分类**：`no_code / syntax_error / runtime_error / timeout / wrong_output / partial / no_final / wrong_final`。

## 解法适配器（文本进文本出，与语言/实现无关）

| 适配器 | 用途 |
|---|---|
| `oracle` | 参考解（含缺陷注入变体），用于**验证流水线判别力**，其读数**不代表能力** |
| `file:<dir>` | 回放已存档的回复（`<dir>/<tid>.txt`），用于离线复判 |
| `command:<shell>` | 外部解法：prompt 从 stdin 进、回复从 stdout 出 |
| `agent` | **真机**：AOT `agenthost -q <prompt>`（py 插件落盘产物），env 覆盖 `PROBE_AGENT_BIN` / `PROBE_AGENT_TIMEOUT` |

取值抽取按**产品真实交付形态**三路收集：① 围栏代码块 ② CLI 回复区裸代码 ③ 回复中指出的落盘产物 → 取**第一个可编译者**（否则取最长）。回复原文一律落 `data/probe/replies/`，失败可回放归因。

## 运行

```bash
python3 eval/probe/tasks.py --selftest                                   # 21/21
python3 eval/probe/grade.py --selftest                                   # 13/13
python3 eval/probe/run_probe.py --selftest                               # 11/11
python3 eval/probe/run_probe.py --kind both --n 3 --seed 20260913 --solver agent --tag=run1
python3 eval/probe/run_probe.py --tasks data/probe/taskset-*.json --solver file:data/probe/replies
```

产物：`data/probe/probe-<solver>-<seed>.json`（摘要：通过率 / 失败模式 / 逐族 / 逐题 / **题集 sha** / 时间）。
