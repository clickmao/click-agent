#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R486 判据器: 读桩请求日志 + 宿主遥测, 按 prereg_r486.json 判定 H1..H4/NC1.
退出码: 0=全部判据成立 1=存在 FAIL 3=缺输入
"""
import json
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
PRE = json.load(open(os.path.join(DIR, "prereg_r486.json"), encoding="utf-8"))
TAGS = ["pre-empty", "pre-plain", "post-empty", "post-plain"]


def count_requests(tag):
    p = os.path.join(DIR, "stub-requests-%s.jsonl" % tag)
    if not os.path.exists(p):
        return None
    n = 0
    with open(p, encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def retry_flags(tag):
    p = os.path.join(DIR, "tel", "tel-%s.jsonl" % tag)
    if not os.path.exists(p):
        return None
    t = f = 0
    with open(p, encoding="utf-8-sig") as fh:
        for line in fh:
            if "retry_skipped" not in line:
                continue
            if re.search(r'"retry_skipped"\s*:\s*true', line):
                t += 1
            else:
                f += 1
    return {"true": t, "false": f}


def main():
    counts = {t: count_requests(t) for t in TAGS}
    flags = {t: retry_flags(t) for t in TAGS}
    missing = [t for t in TAGS if counts[t] is None]
    if missing:
        print("缺输入: %s" % missing)
        print(json.dumps({"counts": counts}, ensure_ascii=False))
        return 3

    pe, pp = counts["pre-empty"], counts["pre-plain"]
    qe, qp = counts["post-empty"], counts["post-plain"]
    res = []

    def add(hid, stmt, ok, evidence):
        res.append({"id": hid, "stmt": stmt, "ok": bool(ok), "evidence": evidence})

    add("H1", "pre_empty - post_empty == 1", (pe - qe) == 1, {"pre_empty": pe, "post_empty": qe, "delta": pe - qe})
    add("H2", "post_empty == 1", qe == 1, {"post_empty": qe})
    add("H3", "pre_empty == 2", pe == 2, {"pre_empty": pe})
    pre_empt_flags, post_empt_flags = flags["pre-empty"], flags["post-empty"]
    add("H4", "post 遥测 retry_skipped=true 且 pre 遥测 retry_skipped=false",
        (post_empt_flags or {}).get("true", 0) >= 1 and (pre_empt_flags or {}).get("false", 0) >= 1,
        {"pre_empt_flags": pre_empt_flags, "post_empt_flags": post_empt_flags})
    add("NC1", "plain 模式 pre == post", pp == qp, {"pre_plain": pp, "post_plain": qp})

    verdict = {"round": "R486", "counts": counts, "retry_flags": flags, "judges": res,
               "pass": all(r["ok"] for r in res), "failed": [r["id"] for r in res if not r["ok"]]}
    with open(os.path.join(DIR, "verdict-r486.json"), "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=1)
    for r in res:
        print("%-4s %-4s %s  %s" % (r["id"], "PASS" if r["ok"] else "FAIL", r["stmt"], json.dumps(r["evidence"], ensure_ascii=False)))
    print("VERDICT:", "PASS" if verdict["pass"] else "FAIL(%s)" % ",".join(verdict["failed"]))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
