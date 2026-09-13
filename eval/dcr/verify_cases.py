#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_cases.py —— 对 eval/dcr/dcr_cases.jsonl 做**独立重算**自验。

读回已序列化的 cases 文件, 对每条 contract 重新走 z3 oracle (与生成器同一独立
oracle, 但此处从**文件内容**重新解析) 并重算标签, 与文件里的 z3_label /
expected_disposition 逐条比对。任何不一致 ⇒ 非零退出。

同时对 out_of_fragment / malformed / absent 三类 (无 z3 真值) 校验其标签来源,
确保它们被显式标注为 n/a 而非被冒充为 z3 结论。

用法: /tmp/z3env/bin/python eval/dcr/verify_cases.py [cases.jsonl]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_cases import (  # noqa: E402
    z3_label_contract, DISPO, _is_structurally_malformed,
)

NO_Z3 = ("out_of_fragment", "malformed", "absent")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "dcr_cases.jsonl")
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    bad, checked, noz = [], 0, 0
    from collections import Counter
    cat = Counter()
    for r in rows:
        cid = r["id"]
        cat[r["category"]] += 1
        if r["category"] in NO_Z3:
            noz += 1
            if r.get("z3_label") != "n/a":
                bad.append((cid, "expected z3_label=n/a for %s, got %r"
                            % (r["category"], r.get("z3_label"))))
            if r.get("self_check") != "ok":
                bad.append((cid, "self_check=%r" % r.get("self_check")))
            continue
        checked += 1
        lab, det = z3_label_contract(r["contract"])
        exp = DISPO[lab]
        if det["z3_label"] != r["z3_label"]:
            bad.append((cid, "z3_label file=%r recomputed=%r contract=%r"
                        % (r["z3_label"], det["z3_label"], r["contract"])))
        if (r["expected_disposition"], r["expected_verdict"]) != exp:
            bad.append((cid, "dispo file=(%r,%r) recomputed=%r"
                        % (r["expected_disposition"], r["expected_verdict"], exp)))
        if r.get("self_check") != "ok":
            bad.append((cid, "self_check=%r" % r.get("self_check")))

    print("cases file : %s" % path)
    print("total      : %d" % len(rows))
    print("z3-checked : %d" % checked)
    print("no-z3      : %d (out_of_fragment/malformed/absent, label_source 显式 n/a)" % noz)
    print("categories : %s" % dict(sorted(cat.items())))
    if bad:
        print("MISMATCH   : %d" % len(bad))
        for cid, msg in bad:
            print("  %s: %s" % (cid, msg))
        return 1
    print("RESULT     : OK — 文件内标签与 z3 oracle 重算完全一致 (0 mismatch)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
