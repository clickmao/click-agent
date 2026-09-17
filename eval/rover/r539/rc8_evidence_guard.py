#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rc8_evidence_guard.py — R539 机检器：**rc=8 不作正确性证据**（判据收窄的机检面）。

背景（R536/R537 观察，见 docs/reports/r536-contract-deadend-and-rc-split.md §6）：
  rc=8「self_test_unmet」= 计划**已跑完**（产物在盘）但**模型自述的 expect_stdout** 与执行器实测冲突。
  它既不是「链成功」也不是「链失败」——**产物的对错只能由外部门禁/隐藏用例（独立判分）判**。
  危险形态：把 rc=8 直接读成「产物没问题」，或者用 rc 数字替代独立判分 ⇒ 假绿。
本器把这条判据钉成可机检项，并自带负控（NC）证明它会红。

检查项（每项独立计分；rc: 0 = 全过 / 1 = 有违规 / 3 = 输入缺失 fail-closed）:
  C1 措辞成对：凡 rc=8 的运行，reason 必同时含「自测未达成」与「产物可疑」，且
     `correctness_asserted == 0`（不许把 rc=8 当正确性断言）。
  C2 判分独立：凡 rc=8 的臂行，其 PASS/失败必须来自独立判分字段（cases_n>0 且 cases_pass 由用例给出）；
     出现「rc=8 ∧ 宣称正确 ∧ 无独立用例」⇒ 违规。rc≠8 不参与本项（rc 与正确性解耦）。
  C3 台账自洽：marker/transcript 的 `correctness_asserted` 只在 rc==0 时为 1。

用法:
  python3 eval/rover/r539/rc8_evidence_guard.py --self-test
  python3 eval/rover/r539/rc8_evidence_guard.py --round r539            # 扫 eval/rover/r539/**/transcript.json + report.json/grade-*.json
  python3 eval/rover/r539/rc8_evidence_guard.py --dir <运行目录>
退出码: 0/1/3（另有 --self-test: 0 = 全部 NC 红 PC 绿 / 1 = 自测不符）。
"""
import argparse
import glob
import io
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def load(p):
    with io.open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def scan_transcripts(root):
    """返回 (transcripts, missing) —— 只认含 rc 字段的 JSON。"""
    found = []
    for p in sorted(glob.glob(os.path.join(root, "**", "transcript.json"), recursive=True)):
        try:
            d = load(p)
        except Exception:
            continue
        if isinstance(d, dict) and "rc" in d:
            found.append((p, d))
    return found


def scan_rows(root):
    """自报臂行（report.json 的 rows ∪ grade-*.json），只作 C2 的输入。"""
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "**", "report.json"), recursive=True)):
        try:
            d = load(p)
        except Exception:
            continue
        for r in (d.get("rows") or []):
            if isinstance(r, dict) and r.get("tid"):
                r = dict(r)
                r["_src"] = os.path.relpath(p, root)
                rows.append(r)
    for p in sorted(glob.glob(os.path.join(root, "**", "grade-*.json"), recursive=True)):
        try:
            d = load(p)
        except Exception:
            continue
        if isinstance(d, dict) and ("all_pass" in d or "cases_n" in d):
            d = dict(d)
            d["_src"] = os.path.relpath(p, root)
            d.setdefault("tid", os.path.basename(p))
            rows.append(d)
    return rows


def check_c1(transcripts):
    bad = []
    for p, d in transcripts:
        if int(d.get("rc", -1)) != 8:
            continue
        reason = str(d.get("reason") or "")
        ca = d.get("correctness_asserted")
        if "自测未达成" not in reason or "产物可疑" not in reason:
            bad.append("%s: rc=8 但 reason 未成对报「自测未达成 ∧ 产物可疑」" % os.path.relpath(p, REPO))
        if ca != 0:
            bad.append("%s: rc=8 但 correctness_asserted=%r (须 0 ⇒ rc 不作正确性证据)" % (os.path.relpath(p, REPO), ca))
    return bad


def check_c3(transcripts):
    bad = []
    for p, d in transcripts:
        rc, ca = int(d.get("rc", -1)), d.get("correctness_asserted")
        if ca is None:
            continue
        if (rc == 0) != (ca == 1):
            bad.append("%s: correctness_asserted=%r 与 rc=%d 不自洽 (只有 rc=0 才断言正确性)" % (os.path.relpath(p, REPO), ca, rc))
    return bad


def check_c2(rows):
    bad = []
    for r in rows:
        rc = r.get("rc", r.get("r1_rc"))
        claims = bool(r.get("all_pass")) or bool(r.get("correct")) or bool(r.get("passed"))
        if rc is None or int(rc) != 8:
            continue
        n = r.get("cases_n")
        passed = r.get("cases_pass")
        if claims and not (isinstance(n, int) and n > 0 and isinstance(passed, int)):
            bad.append("%s: rc=8 却宣称正确，且无独立用例读数 (cases_n=%r cases_pass=%r) ⇒ 把 rc 当判据"
                       % (r.get("_src"), n, passed))
        if claims and isinstance(n, int) and n > 0 and isinstance(passed, int) and passed < n and r.get("all_pass"):
            bad.append("%s: rc=8 ∧ all_pass=true 但 cases_pass=%d/%d 未全过 ⇒ 自报与判分冲突" % (r.get("_src"), passed, n))
    return bad


def run_checks(root):
    ts = scan_transcripts(root)
    rows = scan_rows(root)
    v = check_c1(ts) + check_c3(ts) + check_c2(rows)
    print("RC8_GUARD root=%s transcripts=%d rows=%d" % (os.path.relpath(root, REPO), len(ts), len(rows)))
    for x in v:
        print("VIOLATION " + x)
    print("RC8_GUARD_VERDICT %s" % ("PASS" if not v else "FAIL"))
    return 1 if v else 0


# ---------------- self-test（负控必须红、正向必须绿） ----------------

def _mk(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    return p


def self_test():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="rc8_guard_selftest_")
    ok = True

    def scenario(name, files, rows, want_fail):
        root = os.path.join(tmp, name)
        os.makedirs(root)
        for rel, obj in files:
            _mk(root, rel, obj)
        if rows:
            _mk(root, "w1/report.json", {"rows": rows})
        ts = scan_transcripts(root)
        rr = scan_rows(root)
        viol = check_c1(ts) + check_c3(ts) + check_c2(rr)
        got_fail = bool(viol)
        good = (got_fail == want_fail) and len(ts) >= len(files)
        print("SELFTEST %-28s %s%s" % (name, "PASS" if good else "FAIL",
                                       "" if not viol else "  (%d 条违规)" % len(viol)))
        return good

    REASON_OK = "自测未达成 ∧ 产物可疑; rc=8 不作正确性证据"
    # 正向: rc=8 成对报 + correctness_asserted=0 + 独立判分（30 用例全过）
    ok &= scenario("PC-rc8合规", [("w1/A1-on/t1/transcript.json",
                                   {"rc": 8, "reason": REASON_OK, "correctness_asserted": 0})],
                   [{"arm": "A1-on", "tid": "t1", "rc": 8, "cases_n": 30, "cases_pass": 30, "all_pass": True}], False)
    # NC-A: rc=8 但 correctness_asserted=1（把 rc 当正确性证据）⇒ 必红
    ok &= scenario("NC-A-rc8自称正确", [("w1/A1-on/t1/transcript.json",
                                       {"rc": 8, "reason": REASON_OK, "correctness_asserted": 1})], [], True)
    # NC-B: rc=8 但 reason 未成对（只说"期望不符"，不提产物可疑）⇒ 必红
    ok &= scenario("NC-B-措辞未成对", [("w1/A1-on/t1/transcript.json",
                                      {"rc": 8, "reason": "期望不符", "correctness_asserted": 0})], [], True)
    # NC-C: rc=8 ∧ 宣称正确 ∧ 无独立用例 ⇒ 必红（C2 的主靶）
    ok &= scenario("NC-C-rc当判据", [("w1/A1-on/t1/transcript.json",
                                    {"rc": 8, "reason": REASON_OK, "correctness_asserted": 0})],
                   [{"arm": "A1-on", "tid": "t1", "rc": 8, "all_pass": True}], True)
    # NC-D: rc=8 ∧ all_pass=true 但用例未全过 ⇒ 自报与判分冲突 ⇒ 必红
    ok &= scenario("NC-D-自报判分冲突", [("w1/A1-on/t1/transcript.json",
                                       {"rc": 8, "reason": REASON_OK, "correctness_asserted": 0})],
                   [{"arm": "A1-on", "tid": "t1", "rc": 8, "cases_n": 30, "cases_pass": 12, "all_pass": True}], True)
    # NC-E: rc=0 却 correctness_asserted=0（反向不自洽）⇒ 必红
    ok &= scenario("NC-E-rc0不自洽", [("w1/R1nr/t1/transcript.json",
                                     {"rc": 0, "reason": "链达成", "correctness_asserted": 0})], [], True)
    # 正向2: rc=8 且独立判分 0/30 ⇒ 允许（产物可疑被如实记录，不宣称正确）
    ok &= scenario("PC-rc8如实报错", [("w1/A1-on/t1/transcript.json",
                                     {"rc": 8, "reason": REASON_OK, "correctness_asserted": 0})],
                   [{"arm": "A1-on", "tid": "t1", "rc": 8, "cases_n": 30, "cases_pass": 0, "all_pass": False}], False)

    shutil.rmtree(tmp, ignore_errors=True)
    print("SELFTEST_RESULT %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round")
    ap.add_argument("--dir")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.round:
        rd = a.round.lower()
        rd = rd if rd.startswith("r") else "r" + rd
        root = os.path.join(REPO, "eval/rover", rd)
    elif a.dir:
        root = a.dir
    else:
        print("缺 --round / --dir / --self-test")
        return 2
    if not os.path.isdir(root):
        print("INPUT_MISSING %s (fail-closed)" % root)
        return 3
    return run_checks(root)


if __name__ == "__main__":
    sys.exit(main())
