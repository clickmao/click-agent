#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 台账追加 (幂等 + 键集对齐 + 写后读回; 形态与 append_kpi_q43.py 同源)。"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KPI = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
ROUND = "EXP1-Q44"


def read_rows():
    with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    return lines, [json.loads(l) for l in lines]


def main():
    lines, rows = read_rows()
    if any(r.get("round") == ROUND for r in rows):
        print("IDEMPOTENT_SKIP: %s 已在台账 (lines=%d)" % (ROUND, len(lines)))
        return 0
    keys = list(rows[-1].keys())
    body = {
        "round": ROUND,
        "ts": time.strftime("%Y-%m-%dT%H:%M+0800"),
        "kind": "self-check / 状态探针 v5(D8+D9): ① 路由优先序=权威源优先(主报告 §7 最新块 > 计划看板) "
                "② 两类**非状态形态**围栏(闭合陈述 / 引用形态) ③ 主报告 §7 块增量回填 R401–R412 "
                "④ rc 假绿检测器。窗口 = 对侧(30m 作业) R509 提交(08:09:10)后的**空闲**窗口 ⇒ 本 tick 允许跑真机全量",
        "artifact": "eval/capability/exp1-q44/{prereg_q44.json,verdict_q44.json,verdict_q44_d9.json,"
                    "verdict_q44_d9_docfix.json,selftest_v5.txt,selftest_v5d9.txt,status_v4.json,"
                    "status_v5.json,status_v5_D8.json,status_v5d9.json,status_v5d9_firstmeasure.json,"
                    "status_v5d9_legacyroute.json,fulltest_q44.raw.txt,scan_pipe_rc.py,census_401_412.py,"
                    "backfill_401_412.json,diff_q44.py,diff_q44_d9.py,edit_block_q44.py}; "
                    "scripts/capability_cycle_status.py (v5/D8+D9); "
                    "docs/reports/dynamic-telemetry-eval-rollback-strategy.md (§7 块)",
        "change": "① `decide_route`: 新增 route{primary,first,priority,rule,comparable_from} —— 权威源(§7 最新块)优先; "
                  "open_items/mode/open_count **逐字不变**(纯增量) + `--legacy-route` 负控复现 v4 优先序; "
                  "② D9 `_closed_after`(标记后 30 字符内含 关闭/闭合/已回填/已补/不再/已修 ⇒ close_fenced) 与 "
                  "`_quoted`(标记落在成对 反引号/「」/『』 内 ⇒ quoted_fenced) —— 命中被围栏后**继续检查后续 marker**, "
                  "同字段真开放项仍入账; ③ §7 块**增量**改写(行锚点替换+读回校验+幂等): 最近一轮/HEAD/机检/器具取证/"
                  "R401–R412 回填表(12 行)/文档同步, 290→307 行; ④ `scan_pipe_rc.py`(日志面假绿 + 脚本面管道末段 rc, "
                  "rc 语义 0/1/2/3 分层); ⑤ `census_401_412.py`(机取来源, 禁凭记忆)",
        "readings": "真机 A/B(D8, 判据器 6/6 rc=0): v4(HEAD) vs v5 共享字段**逐字相同**(mode/open_count/open_items/"
                    "open_items_detail/backlog_open/master_open/sources) ∧ 字段集只增不减(added route,rule_v5, removed 0) ∧ "
                    "route.primary=master-block ∧ priority_len=9=8+1 ∧ 负控(--legacy-route)=backlog | "
                    "selftest: v5/D8 30/30 → v5/D9 **34/34** PASS | "
                    "D9 首测: master hits **3→2**, close_fenced=0/quoted_fenced=0(缺围栏) ⇒ **P8 FAIL**(预注册部分否证) → "
                    "docfix 重测(文档侧把缺陷名加「」): hits **3→1**, close_fenced=3, quoted_fenced=1, 判据 6/6 rc=0, "
                    "真开放项(improvements.md R404–R416)保留 | "
                    "q44 真机全量: **1643 / 失败 0 / 跳过 0**(38 s, `FULLTEST_EXIT=0` 由显式标记取, 非管道末段) | "
                    "rc 检测器: `/tmp/r508_fulltest.log` ⇒ rc=1 FALSE_GREEN(Failed:1 vs TEST_RC=0); 仓内 251 个 .sh **0 命中**; "
                    "检测器自检 9/9 | census: R401–R412 **11/12** 有独立证据目录(R404 例外, 读数在 eval/bge 与后续计划交叉引用)",
        "honest_boundaries": "① D9 预注册 P8 **首测 FAIL 不翻案**: 真仓当时只有闭合围栏命中(引用围栏 0); 旧读数原样保留于 "
                             "verdict_q44_d9.json, 文档侧按「把引用写显式」改后**单列** verdict_q44_d9_docfix.json。"
                             "② P7 的数值期望(3→2)随语料有意改写**重算为 (3→1)**(改写语料=改写测量对象), CLI 参数与 ns 入档, "
                             "非放宽断言(不变量 post<pre ∧ 假阳性行不在 route.first 仍逐条判)。"
                             "③ `/tmp/r508_fulltest.log` 的单条失败(FrontendAskSameConnTests)在 q44 真机全量中**未重现** ⇒ "
                             "未定论(可能其后已修 / 可能网络型偶发), 不宣称对侧缺陷。"
                             "④ 假绿影响面**未扩大**: `eval/rover/r508` 下 grep `1636`/`TEST_RC` **0 命中** ⇒ 未发现已提交证据"
                             "依赖该临时记录, 不宣称对侧结论失效。"
                             "⑤ 块内仍留**一条真开放项**(improvements.md 的 R404–R416 轮节未回填) ⇒ master_open=1, "
                             "route.first 指向它(有意保留, 不是漏围栏)。"
                             "⑥ R404 无独立证据目录 ⇒ 如实标注, 不假装 12/12 同级。"
                             "⑦ 本 tick **未**代对侧改动任何产物(其 scripts/ 与 eval/rover 只读)。",
        "next": "① improvements.md 的 R404–R416 轮节回填(文档轮; 现为 route.first 指向项)。"
                "② 把「rc 必须由发射点显式写标记 + 日志面矛盾闸」落到**仓内可复用**位置(对侧 harness 模板)。"
                "③ decide 是否在 §7 块保留「最近 N 轮」窗口(现为最新一轮 + R401–R412 历史锚 + improvements.md 指针)。"
                "④ 补齐 exp1-q39/q40/q41/q42 台账缺行(上轮已登记未做)。",
        "owner_round": ROUND,
    }
    row = {k: body.get(k, "") for k in keys}
    assert set(row.keys()) == set(keys) and len(row) == len(keys)
    with open(KPI, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    lines2, rows2 = read_rows()
    ok = (len(lines2) == len(lines) + 1 and rows2[-1].get("round") == ROUND
          and len(rows2) == len(lines2))
    print("KPI_APPEND lines %d→%d last_round=%s readback_ok=%s keys_match=%s"
          % (len(lines), len(lines2), rows2[-1].get("round"), ok, list(rows2[-1].keys()) == keys))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
