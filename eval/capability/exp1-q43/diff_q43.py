#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q43 判据器: 来源② 换口径的前后对比 (逐字段 + 预注册判据 P1..P6)。

口径契约 (先 dump 真实键路径再写读取, 技能硬规则④):
  status_*.json 顶层键: mode / open_count / open_items / open_items_detail / backlog_open /
                        master_open / sources{backlog{rows_scanned,closed,unmarked,tables,state_col},
                        master{hits,format_matched,note,...}} / kpi_lines / last_probe / skills_count / rule
rc 语义: 0 全过 / 1 被测不满足 (P* 有假) / 3 输入缺失 (fail-closed, 不计入被测读数)
"""
import json
import os
import re
import sys

D = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(D, "status_before_q43.json")
AFTER = os.path.join(D, "status_after_q43.json")
SELFTEST = os.path.join(D, "selftest_q43.txt")


def load(p):
    with open(p, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def main():
    for p in (BEFORE, AFTER, SELFTEST):
        if not os.path.exists(p):
            print(json.dumps({"rc": 3, "error": "missing input", "path": p}, ensure_ascii=False))
            return 3
    b, a = load(BEFORE), load(AFTER)
    st = open(SELFTEST, encoding="utf-8-sig", errors="replace").read()

    def src1(items, detail):
        return sorted(x["item"] for x in detail if x.get("kind") == "plan-item" or
                      re.match(r"^R\d+", x["item"] or ""))

    checks = {}

    # P1 块级定位 (来源② 输入面覆盖 > 0)
    mdiag = a["sources"]["master"]
    checks["P1_block_located"] = bool(mdiag.get("block_found")) and int(mdiag.get("block_fields") or 0) >= 5

    # P2 单变量: 来源① 读数逐字段不变
    checks["P2_src1_backlog_open_unchanged"] = b["backlog_open"] == a["backlog_open"] == 8
    checks["P2_src1_items_unchanged"] = src1(None, b["open_items_detail"]) == src1(None, a["open_items_detail"])
    checks["P2_src1_backlog_diag_unchanged"] = (
        json.dumps(b["sources"]["backlog"], ensure_ascii=False, sort_keys=True) ==
        json.dumps(a["sources"]["backlog"], ensure_ascii=False, sort_keys=True))

    # P3 真实开放项可见 (来源② 首次真正进入输出)
    s2 = [i for i in a["open_items"] if i not in b["open_items"]]
    checks["P3_src2_item_visible"] = len(s2) >= 1
    checks["P3_src2_item_names_gap"] = any(("缺口" in i) or ("未回填" in i) for i in s2)
    checks["P3_format_matched_true"] = mdiag.get("format_matched") is True
    checks["P3_before_was_zero"] = (b["sources"]["master"].get("hits") == 0 and
                                    b["sources"]["master"].get("format_matched") is False)

    # P4 自检全绿 (含新增用例与负控)
    npass, nfail = len(re.findall(r"^PASS", st, re.M)), len(re.findall(r"^FAIL", st, re.M))
    checks["P4_selftest_no_fail"] = nfail == 0 and npass >= 20
    checks["P4_new_cases_present"] = all(k in st for k in
                                         ("T12", "T13", "T14", "T15", "T16", "N5", "N6", "N7"))

    # P5 负控有判别力 + 反空心
    checks["P5_N5_legacy_misses_new_form"] = "PASS  N5" in st
    checks["P5_N7_negation_fence"] = "PASS  N7" in st

    # P6 「空」≠「缺失」双向可区分
    checks["P6_T13_block_found_but_closed"] = "PASS  T13" in st
    checks["P6_T14_no_block_is_missing"] = "PASS  T14" in st

    # 预注册原陈述的**事后单列** (不翻案: 原陈述判 FALSIFIED, 修正后的更强陈述另记; 技能「预注册被证伪」纪律)
    checks_posthoc = {
        "P5_orig_prereg_legacy_zero_hits": {
            "registered": "legacy(v3) 在 T12 夹具上命中数 == 0",
            "measured": "legacy 命中 1 条 = 历史快照段 R900; 真开放项(状态回填缺口) 0 命中",
            "status": "FALSIFIED",
            "handling": "N5 改判为更强的成对陈述(漏真项 ∧ 错命中历史段, 两条同时成立); 原陈述不翻案",
        }
    }

    # 归属/边界
    checks["X_only_new_items_from_src2"] = all(
        any(k in i for k in ("缺口", "未回填", "待定", "进行中", "未开始", "欠", "部分", "计划中"))
        for i in s2)
    checks["X_src2_fields_exposed"] = len(mdiag.get("block_field_texts") or []) >= 5
    checks["X_neg_fenced_visible"] = "neg_fenced" in json.dumps(mdiag, ensure_ascii=False)

    bad = sorted(k for k, v in checks.items() if not v)
    out = {"rc": 0 if not bad else 1, "round": "EXP1-Q43", "owner": "self",
           "checks": checks, "checks_posthoc": checks_posthoc, "failed": bad,
           "before": {"mode": b["mode"], "open_count": b["open_count"], "master": b["sources"]["master"]},
           "after": {"mode": a["mode"], "open_count": a["open_count"], "master_diag":
                     {k: v for k, v in mdiag.items() if k != "block_field_texts"},
                     "block_fields_n": len(mdiag.get("block_field_texts") or [])},
           "new_items_from_src2": s2}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
