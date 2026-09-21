# R621 DAG（RF0004.2 · M3 第五刀 = 等价面分辨率取证 + 判据分级）

**意图 → 子任务图**（用户令「DAG 先行」；本文件为该令的落盘载体）

```
N0 起手闸 ────────────────────────────┐
   (preflight + 内存清场 + 前 swing 重派生) │
                                        ▼
N3 预注册(先写后跑) ──→ N5 真机臂(39 跑次) ──→ N6 判据器行使 ──→ N7 铁律11 前置器 ──→ N8 收口五件
   (prereg-r621.json)      T×18/C×18/C1×9      verdict+kpi-table     precond-r621.json   + status_gen --check
        ▲                     w217..w219                                                        │
N2 判据改版 + 影子自检 ─────────┘（判据 v4 必须先于 N6 可用）                                     │
   (judge_r621.py / selftest 11/11)                                                             ▼
                                                                                        逐名列名提交
N1 主线提醒(只读)  ─┐
N4 文献小步(只读网络)─┴─ 与 N5 并行面（均只读，不触在飞件：judge/runner/prereg 在臂运行期只读）
```

## 节点与依赖边

| 节点 | 内容 | 依赖边 | 产出件 |
|---|---|---|---|
| N0 | 起手闸：`roundcheck.py preflight`（min-avail 2900 / min-disk 1 / need-key）+ 清 VBCSCompiler/MSBuild/pyright（-200 MB）+ 运行器自带三段采样闸 | — | `gate-margin-r621.json` |
| N1 | 主线提醒：读 `iteration-master-plan.md` §7 / `improvements.md` 最新 / `docs/plans/` 最新计划 | — | 报告结论行（1 行） |
| N2 | 判据改版 v4：J6 三态化（阈值 = 同臂逐跑次用例数极差）+ rc 分级（0/1/2/3，J6 移出 `instrument_defects`）+ **影子自检** | — | `judge_r621.py` · `selftest_judge_r621.py`（11/11 PASS） |
| N3 | 预注册（先写后跑闸）：单变量轴/held-constant/`baselines` 引用/falsification 七条/rc 分级表 | N0 | `prereg-r621.json`（v3 修订，21:36 落盘） |
| N4 | 文献小步：arXiv ≤3 query / 摘要取件 ≤2 / 只读网络 | — | `docs/research/lit-review-ledger.md` §18 |
| N5 | 真机臂：T(exec=1)×6/窗 · C(exec unset)×6/窗 · C1(codex 真值)×1/窗，窗集 w217..w219 | N0∧N3 | 逐跑次原始读数 + `logs/run-samples.jsonl` |
| N6 | 判据器行使：J0..J6 + J6_state + `mechanism_secondary_failures` | N2∧N5 | `verdict-r621.json` · `kpi-table-r621.json` |
| N7 | 铁律 11 前置器：`eval/rover/r507pre/exec_precondition.py --round R621`（两侧产物物化+真跑） | N5 | `precond-r621.json`（rc 决定成本/质量是否可验收） |
| N8 | 收口五件 + 形式校验 | N6∧N7 | `bins/evidence-run/kpi.jsonl 行(带 baselines)/registry 行` + `status_gen.py --check` PASS + 提交 |

## 可并行面（纪律）

- **允许并行**：`{N1, N4}` 与 `N5` —— 二者均为**只读**（读文档 / 读网络），不写任何在飞件。
- **禁并行**：N6/N7/N8 与 N5 不得重叠；N2 的产物（judge/selftest）在 N5 运行期**禁再生成**（面在飞不得编辑该面会调用的器具）⇒ derive 的再次运行**推迟到 N5 结束后**。
- 本轮实际：N4 在 N5 在飞期间只读执行（arXiv 3 query / 摘要 1 取件），未占真机预算、未写任何在飞件。

## 收尾判据：该重启哪条边（禁重跑全轮）

| 现象 | 重启边 | 依据 |
|---|---|---|
| 前提闸 rc≠0（legacy 档仍给候选 / 前缀 ≠ legacy 锚） | 只重启 **N3→N5** | falsification ①（判据不动、不重跑收口） |
| J0 未过（两臂不可区分 / 前缀不同源） | 整轮 VOID，重启 **N5**（查器具/环境） | falsification ②（rc=2 禁作被测结论） |
| J6 = `NO_RESOLUTION` | **不重启**：按 R5 记「本轴非承重变量」定案关闭、换杠杆 | falsification ③（禁为同一缺口再加轮） |
| 有效窗 < 2 | rc=3 停链，重启 = **扩窗集**（新窗号，不改阈值） | falsification ⑥ |
| `status_gen --check` 红 / registry 钉错 | 只重启 **N8**（收口），不重跑测量 | 派生件缺失只重跑后处理 |
| 器具自检未过 | 只重启 **N2**，先修自检再谈读数 | falsification ⑦ |

## 诚实偏差登记

- **N1/N4 次序**：本轮先起臂（21:36）后补文献小步（22:0x），与 §2「文献小步在预注册之前」的次序不同 ⇒ 已在报告与台账里如实登记，未静默跳步（文献为只读、不影响预注册内容）。
- **本 DAG 落盘时刻晚于起臂**（起臂后补写）：DAG 结论与依赖边由起臂时已执行的顺序反推，未改动任何已跑读数；后续轮次按本文件在**起臂前**落盘。
- **N2 的 J6 状态机在起臂前被影子自检抓到「比较变量写反」**（Δ 符号约定）：按「修代码不放宽断言」处置 —— 改状态机 + 把符号约定写进字段名 `delta_median_C_minus_T`，并新增两例控制（11/11 PASS）后才起臂。
