# EXP1-Q43 · 路由器器具 D7 修复 (来源②输入面覆盖 = 0 ⇒ 换口径)

**归属**: `self` (本侧实施 + 本侧自跑读数)。**轮号**: EXP1-Q43 (不占主线轮号; 主线 R508 由对侧会话在飞)。
**窗口**: 对侧 R508 会话正在跑全量 `dotnet test` (07:05 起, VBCSCompiler + MSBuild 节点在飞) ⇒ 本 tick 零冲突:
不碰产品源码 / 不跑 dotnet / 不占主线轮号 (真缺陷 71 + 起手闸纪律)。

## 为什么是本轮做器具而不是推进计划项

检测器真机读数: `mode=tasks, open_count=8`, 但 8 项**全部**来自来源①(`v0.22.0` 计划看板的沉积行 —
R370/R371「进行中」+ exp1..exp8), 而来源②(主报告 §7 = 宪法级主线状态的权威落点)是:

```json
{"hits": 0, "format_matched": false,
 "note": "该来源对当前报告版式零命中 ⇒ 视作「缺失」而非「无未完成事项」(v2 显式化)"}
```

⇒ 主线**最新状态块一个字符都没进输出**, 分支判定完全由 v0.22.0 沉积行驱动, 与宪法级主线定义
(`iteration-master-plan.md` §0-0 铁律 10: 外部真值对照自检) 方向错位。
按技能硬规则④「裁决器/判据器报 RED 的第一假设是器具读法错」先修路由器具, 不动被测。

## 根因 (D7)

v3 的 `MASTER_PAT` 是**四条固定词面**(`下轮候选` / `待确认` / `本轮待办` / `进行中`), 而主报告 §7 的最新块
早已换成另一种版式 (`> ### ⏱ 最新状态` + `**主线**` / `**状态回填缺口**` / `**诚实边界**` 字段列表)
⇒ 零命中。与 v2/D3、v3/D5 同族: **靠词面找条目 ⇒ 版式一改就静默失配**。

## 修法 (换口径, 不加词面)

1. **块级定位** `_status_block`: `## 7.` 后第一段 `>` 引用块, 遇**第二个**块内标题即止(其后是历史快照)。不依赖任何专有词面。
2. **全字段原文入账** `block_field_texts` (≤12 条 × 200 字符), 由读者判 —— 与来源① `other_cells` 同口径。
3. **机械 hint** = 既有 `OPEN_MARKERS` + `缺口/未回填/未同步/待补/待裁决`, 并过**否定围栏**(命中处前 20 字符含
   `无/没有/不存在/未设/禁止/非` ⇒ 记 `neg_fenced`, 不判 open; 与 R299/R308b 同族)。
4. `block_found` / `block_lines` / `block_fields` / `neg_fenced` / `legacy_form_hits` 全部入 diag ⇒ **「空」与「缺失」双向可区分**。
5. 旧四条词面降为 `MASTER_PAT_LEGACY`, 只用于负控; `hits` / `format_matched` **字段语义不变** ⇒ T1–T11 / N1–N4 逐条原样, **未放宽任何断言**。

## 读数

| 面 | before | after |
|---|---|---|
| mode / open_count | tasks / 8 | tasks / 9 |
| 来源② diag | `hits=0, format_matched=false, note=零命中` | `block_found=true, block_lines=15, block_fields=12, hits=1, neg_fenced=0, legacy_form_hits=0, format_matched=true` |
| 来源② 入账项 | (无) | `状态回填缺口（如实标注）: R401–R412 逐轮条目未回填…` |
| 来源① | `backlog_open=8, rows_scanned=14, closed=4, unmarked=2, tables=5` | **逐字段不变** (单变量) |
| 判定器自检 | — | **24/24 PASS** (T1–T17 + N1–N7, FAIL=0) |
| 判据器 | — | `verdict_q43.json` rc=0, `failed=[]` |

复现: `bash eval/capability/exp1-q43/run_q43.sh` (纯 stdlib, 不触发 dotnet build)。

## 诚实边界

1. **预注册 P5 被实测否证**: 原陈述「legacy 在 T12 夹具上命中数 == 0」不成立 —— v3 实测是
   「**漏真项**(状态回填缺口 0 命中) ∧ **错命中历史段**(R900)」, 假阴性 + 假阳性并存。处置 = N5 改判为
   **更强**的成对陈述(两条同时成立才算有判别力), 原陈述与实测值单列 `checks_posthoc`, **不翻案**。
2. 来源② 仍**不接管** mode: 本轮只修输入面覆盖与可见性; 「最新块无开放项 ⇒ 直接 selfcheck」列为独立预注册轮。
3. 词表 hint 仍可能漏判非词面表述 ⇒ 全字段原文入账是兜底, 机械命中仅作 hint。
4. 否定窗 20 字符 + 单字「无」偏保守(宁可漏判 open, 不误判 open)。
5. 本轮**未跑** dotnet 形式门: 未改登记表/证据映射(机械上不触发) **且**窗口被对侧全量测试占用(禁并行 build)。
6. 台账缺口(**未代填**): `eval/capability/exp1-q39..q42` 目录存在而 `kpi.jsonl` 无对应行。
7. 窗口内对侧证据(只读复核, 归属 `foreign`): `/tmp/r508_fulltest.log` 同批出现
   `Failed: 1, Passed: 1635, Total: 1636` 与 `TEST_RC=0` —— `TEST_RC` 取自 `dotnet test … | tail -8` 的
   **管道末段** ⇒ rc 恒 0 (R409 同族假绿); 未替对侧改动任何文件。
