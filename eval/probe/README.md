# eval/probe — 随机化能力自检探针（exp14）

> 长期任务：用**随机程序题**与**随机数学题**给本 agent 做能力自检，并把经验抽象成**语言无关的通用性 skill** 落 `skills/`。
> 计划：`docs/plans/v0.24.0-exp14-random-probe-selfcheck.md`、`docs/plans/v0.25.0-r399-probe-hardening-and-kpi.md`

## 文件

| 文件 | 行数 | 作用 |
|---|---|---|
| `tasks.py` | 853 | 随机题集生成器：程序 7 族（含陷阱族）+ 数学 6 族 + **见证型 2 族**；对抗用例只注入 hidden；每答双路径验算，不一致则拒绝发题；`--selftest` 39 条负控 |
| `grade.py` | 406 | 判定器：沙箱执行 + 隐藏用例比对 + **失败模式分类** + 判定器自身反向负控 + **见证独立验证**；`--selftest` 25 条 |
| `run_probe.py` | 440 | 编排器：题集（族池含见证族）→ 适配器 → 判定 → 结构化摘要；`--families` 定向覆盖 / `--dump-tasks` 出题落盘；`--selftest` 18 条 |
| `../../scripts/kpi_probe.py` | 418 | **跑测数据打点**：运行摘要 × 遥测 token → 台账 `data/probe/kpi.jsonl` + 前后对比报告；`--selftest` 20 条 |

## 判分口径（四条铁律）

1. **只认隐藏用例**：公开样例只用于题面，从不参与判分。
2. **整题全对才算过**：用例级通过率会给出作弊空间（实测：硬编码公开样例的解在 v1 题集拿 22.2% 用例通过率，加硬后降到 6.25%，**整题全对 0**）。
3. **失败必须分类**：`no_code / syntax_error / runtime_error / timeout / wrong_output / partial / no_final / wrong_final / wrong_witness`。
4. **判定口径假设错 ⇒ 反向空心指标**：判定器必须按产品真实交付形态取材（无围栏裸代码 / 尾部 CLI 状态行），且必须带真机形态负控。

## 题集加硬（M6）

- **对抗用例**（`tasks.py` `HARD_INPUTS`）：全负数组 / 单元素 / 边界长度 / 极大值 / 并列 / 重复，**只进 hidden**；单族对抗用例 <3 条 ⇒ 拒绝发题。
- **陷阱族** `pair_closest_abs_sum`：两数之和绝对值最小（并列取数值最小）——陷阱=同值可复用于不同下标、负数、全零。
- **见证型数学族**（判定=**独立验证见证**，非比对标签）：
  - `witness_sqrt_mod`：求 `x` 使 `x²≡a (mod p)`，**多解合法**，判定端验 `x²mod p==a`；
  - `witness_min_counterexample`：求最小 `n` 使 `P(n)` 假，判定端自行复核「n 假 ∧ 所有 n′<n 真」。
  - 生成器侧 `answer` 仅供 oracle 正控产出**一个**合法见证；判定端不复用生成器路径。

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
python3 eval/probe/tasks.py --selftest          # 39/39
python3 eval/probe/grade.py --selftest          # 25/25
python3 eval/probe/run_probe.py --selftest      # 18/18
python3 scripts/kpi_probe.py --selftest         # 20/20

# 全量（对抗用例生效）
python3 eval/probe/run_probe.py --kind both --n 3 --seed 20260913 --solver agent --tag=run1
# 定向覆盖新族
python3 eval/probe/run_probe.py --kind both --n 3 --seed 20260913 \
  --families pair_closest_abs_sum,witness_sqrt_mod,witness_min_counterexample \
  --solver oracle --dump-tasks data/probe/taskset-m6.json --tag=m6
python3 eval/probe/run_probe.py --tasks data/probe/taskset-m6.json --solver agent
# 跑测数据打点 + 前后对比
python3 scripts/kpi_probe.py --compare probe-oracle probe-agent
```

产物：`data/probe/probe-<solver>-<seed>.json`（摘要：整题全对 / 用例级通过率 / 失败模式 / 逐族 / 逐题 / **题集 sha** / 时间），
台账 `data/probe/kpi.jsonl`，对比报告由 `scripts/kpi_probe.py --report <path>` 输出。
