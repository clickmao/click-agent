# EXP1-Q44 — 状态探针 v5(路由优先序) + 两类非状态形态围栏 + §7 块 R401–R412 回填 + rc 假绿取证

- **窗口**: 主线 30m 作业 (`9a97763d5fcd`) 于 **08:09:10** 提交 R509 后**空闲** ⇒ 起手核过「无 `.git/*.lock` / 无
  `dotnet|run_*.sh` 活体 / `/tmp` 最新非本侧产物 08:09」才跑真机全量（纪律：兄弟作业在飞即停手）。
- **候选台账（用户令：全部候选并一轮）**

| # | 候选（Q43 的 `next`） | 状态 | 产出 / 原因 |
|---|---|---|---|
| C1 | mode/推进对象由「§7 最新块开放项」优先决定 | **做** | v5/D8 `decide_route` + `route.*` 字段；真机 A/B 6/6 rc=0；selftest 30/30 |
| C2 | 对侧 harness 假绿：记录 rc 必须 fail-closed | **做** | `scan_pipe_rc.py`（日志面假绿 + 脚本面管道 rc，rc 分层 0/1/2/3，自检 9/9）；真机取证 `/tmp/r508_fulltest.log` ⇒ **rc=1 FALSE_GREEN**；仓内 251 个 `.sh` **0 命中** |
| C3 | 主报告 §7 最新块刷新到最近一轮 | **做** | 增量改写（行锚点 + 读回校验 + 幂等）：最近一轮 R509 / HEAD / 机检 / 器具取证 / 文档同步，290→307 行 |
| C4 | 补 R401–R412 状态回填 | **做** | `census_401_412.py` 机取来源 ⇒ 块内 12 行回填表；**11/12 有独立证据目录**，R404 例外（如实标注） |
| D9 | （本轮新发现，非计划项）v5 自身两条假阳性 | **做** | `_closed_after` / `_quoted` 围栏 + `close_fenced`/`quoted_fenced` 可见；selftest 34/34 |

- **读数**

| 判据 | 读数 | 证据 |
|---|---|---|
| D8 零回归（纯增量） | v4(HEAD) vs v5 共享字段**逐字相同**；字段集只增不减 | `verdict_q44.json` 6/6 rc=0 |
| D8 权威源优先 | `route.primary=master-block`、`priority_len=9=8+1`；负控 `--legacy-route` ⇒ `backlog` | 同上（P1/P3/P4） |
| D9 首测 | master hits **3→2**；`close_fenced=0/quoted_fenced=0` ⇒ **P8 FAIL（预注册部分否证）** | `verdict_q44_d9.json` 5/6 **rc=1（原样保留）** |
| D9 docfix 重测 | hits **3→1**、`close_fenced=3`、`quoted_fenced=1`，真开放项保留 | `verdict_q44_d9_docfix.json` 6/6 rc=0 |
| 探针自检 | v5/D8 **30/30** → v5/D9 **34/34**（T1–T25 + N1–N9） | `selftest_v5.txt` / `selftest_v5d9.txt` |
| 真机全量（本侧，显式标记 rc） | **1643 / 失败 0 / 跳过 0**（38 s，`FULLTEST_EXIT=0`） | `fulltest_q44.raw.txt` |
| 形式门禁（登记/文档面） | **14/14**（`FORMGATE_EXIT=0`） | `formgate_q44.raw.txt` |
| rc 假绿检测器自检 | **9/9**（好/坏日志、无判定行、缺文件、好/坏脚本成对） | `scan_pipe_rc.py --selftest` |

- **复现**

```bash
python3 scripts/capability_cycle_status.py --selftest
python3 eval/capability/exp1-q44/diff_q44.py                     # D8 A/B
python3 eval/capability/exp1-q44/diff_q44_d9.py --out verdict_q44_d9_docfix.json --expect-hits 3,1
python3 eval/capability/exp1-q44/scan_pipe_rc.py --selftest
python3 eval/capability/exp1-q44/scan_pipe_rc.py --check-log /tmp/r508_fulltest.log   # rc=1 假绿
python3 eval/capability/exp1-q44/census_401_412.py
```

- **诚实边界**
  1. D9 预注册 **P8 首测 FAIL 不翻案**：首测真仓只有闭合围栏命中；文档侧按「把引用写显式」加引号后的重测**单列**，
     不放宽判据。P7 的数值期望随语料有意改写由 (3,2) 重算为 (3,1)（CLI 参数 + ns 入档）。
  2. `/tmp/r508_fulltest.log` 的单条失败（`FrontendAskSameConnTests`）在本轮真机全量中**未重现** ⇒ 未定论。
  3. 假绿**影响面未扩大**：`eval/rover/r508` 下 grep `1636`/`TEST_RC` **0 命中** ⇒ 未发现已提交证据依赖该临时记录，
     不宣称对侧结论失效。缺陷在**对侧临时命令**，仓内脚本 0 命中；本侧**未代对侧改动**任何产物。
  4. 块内仍留**一条真开放项**（improvements.md 的 R404–R416 轮节未回填）⇒ `master_open=1`，`route.first` 指向它
     （有意保留，不是漏围栏）。
  5. R404 无独立证据目录（读数散在 `eval/bge/` 与后续计划交叉引用）⇒ 不假装 12/12 同级。
  6. 前态锚钉 `cc9cafc`（D8 提交）而非 `HEAD`，并断言「是 HEAD 祖先 ∧ 字节与现盘不同」。

- **下轮候选**: ① improvements.md R404–R416 轮节回填（现为 `route.first`）；② 把 rc 显式标记纪律落到仓内可复用位置；
  ③ 决定 §7 块是否保留「最近 N 轮」窗口；④ 补齐 exp1-q39/q40/q41/q42 台账缺行。
