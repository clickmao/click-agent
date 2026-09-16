#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q43 台账追加 (幂等 + 键集对齐 + 写后读回)。

纪律: ① 新行键集 == 既有同族行键集(不增不减) ② 同类运行只追加一次(按 round 去重)
      ③ 写后读回全文件逐行可解析 + 行数 +1 + 末行 round 正确(不采信工具回执)
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KPI = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
ROUND = "EXP1-Q43"


def read_rows():
    with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    return lines, [json.loads(l) for l in lines]


def main():
    lines, rows = read_rows()
    if any(r.get("round") == ROUND for r in rows):
        print("IDEMPOTENT_SKIP: %s 已在台账 (lines=%d)" % (ROUND, len(lines)))
        return 0
    keys = list(rows[-1].keys())          # 键集/键序对齐既有同族行
    body = {
        "round": ROUND,
        "ts": time.strftime("%Y-%m-%dT%H:%M+0800"),
        "kind": "self-check / 路由器器具 D7 (来源②输入面覆盖=0: 主报告 §7 最新块对四条固定词面零命中) ⇒ 换口径: "
                "块级定位 + 全字段原文入账 + 否定围栏; 活跃会话(R508 全量 dotnet test)窗口内的零冲突轮, 不跑 dotnet/不占主线轮号",
        "artifact": "eval/capability/exp1-q43/{prereg_q43.json,status_before_q43.json,status_after_q43.json,"
                    "selftest_q43.txt,verdict_q43.json,diff_q43.py,run_q43.sh}; scripts/capability_cycle_status.py (+v4/D7)",
        "change": "① 块级定位 (_status_block: `## 7.` 后第一段 `>` 引用块, 遇第二个块内标题即止) —— 不依赖任何专有词面; "
                  "② 块内全部 `**字段**` 原文入 block_field_texts 由读者判(与来源① other_cells 同口径); "
                  "③ 机械 hint 复用 OPEN_MARKERS + 缺口/未回填/未同步/待补/待裁决 + 否定围栏(前 20 字符含 无/没有/不存在/未设/禁止/非 ⇒ neg_fenced 不判 open); "
                  "④ block_found/block_fields/neg_fenced/legacy_form_hits 全部入 diag ⇒「空」≠「缺失」双向可区分; "
                  "⑤ 旧四条词面降为 MASTER_PAT_LEGACY(仅负控), hits/format_matched 语义不变 ⇒ T1–T11/N1–N4 逐条原样未放宽",
        "readings": "before: mode=tasks open_count=8 (来源① 8 项 · 来源② {hits:0,format_matched:false,note:零命中}) | "
                    "after: 来源② {block_found:true, block_lines:15, block_fields:12, hits:1, open_matched:1, "
                    "neg_fenced:0, legacy_form_hits:0, format_matched:true} ⇒ 首次入账真开放项「状态回填缺口(R401–R412 未回填)」; "
                    "来源① 逐字段不变(backlog_open=8 · rows_scanned14 · closed4 · unmarked2 · tables5 · state_col 全同 · items 逐项相同) = 单变量; "
                    "selftest 24/24 PASS (T1–T17 + N1–N7, FAIL=0); verdict rc=0 failed=[]",
        "honest_boundaries": "① 预注册 P5 初版陈述「legacy 在 T12 夹具上 0 命中」被实测**否证** —— v3 实测是「漏真项(缺口) ∧ "
                             "错命中历史段(R900)」; N5 改判为更强的成对陈述, 原陈述单列 checks_posthoc, 不翻案。"
                             "② 来源② 仍**不接管** mode/分支: 本轮只修输入面覆盖与可见性; 「最新块无开放项 ⇒ 直接 selfcheck」= 独立预注册轮。"
                             "③ 词表 hint 仍可能漏判非词面表述的开放项 ⇒ 全字段原文入账是兜底(读者判), 机械命中仅作 hint。"
                             "④ 否定回看窗 20 字符 + 单字「无」偏保守(宁可漏判 open, 不误判 open)。"
                             "⑤ 本轮**未跑** dotnet 形式门: 未改登记表/证据映射(机械不触发) + 窗口被对侧 R508 全量测试占用(禁并行 build, 真缺陷 71)。"
                             "⑥ 台账缺口(未代填): exp1-q39/q40/q41/q42 目录存在而 kpi.jsonl 无对应行。"
                             "⑦ 窗口内对侧证据(只读复核, 归属 foreign): /tmp/r508_fulltest.log 同批出现 `Failed: 1, Passed: 1635, Total: 1636` 与 `TEST_RC=0` "
                             "—— TEST_RC 取自 `dotnet test … | tail -8` 的管道末段 ⇒ 恒 0(R409 同族假绿), 未替对侧改动。",
        "next": "① 让 mode 由「最新块开放项」优先决定(独立预注册轮, 会改路由可比性)。② 对侧 harness 假绿: 记录 rc 必须 fail-closed"
                "(显式标记而非管道末段)。③ 主报告 §7 最新块刷新到 R508(对侧收口中, 本侧不抢)。④ 补 R401–R412 状态回填"
                "(文档轮; 本轮已首次由探针机械入账)。",
        "owner_round": ROUND,
    }
    row = {k: body.get(k, "") for k in keys}          # 键集/键序 == 既有同族行
    assert set(row.keys()) == set(keys) and len(row) == len(keys)
    with open(KPI, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 写后读回 (不采信回执)
    lines2, rows2 = read_rows()
    ok = (len(lines2) == len(lines) + 1 and rows2[-1].get("round") == ROUND
          and len(rows2) == len(lines2))
    print("KPI_APPEND lines %d→%d last_round=%s readback_ok=%s keys_match=%s"
          % (len(lines), len(lines2), rows2[-1].get("round"), ok, list(rows2[-1].keys()) == keys))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
