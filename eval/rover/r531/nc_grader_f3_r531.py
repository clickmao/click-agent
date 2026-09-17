#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 F3 双判分器红绿对齐 NC: 两套非同源判分器 (前置器用例脚本 / 冻结期独立判分器) 必须给出同一组红绿。

正控: oracle 树 ⇒ 两侧 30/30 rc=0。负控: qr_offby1 / choose_nomod / extra_text / empty 树 ⇒ 两侧 rc≠0 且
**通过数与失败例集合一致** (只判分器间不一致 ⇒ 记 MISALIGNED 并 rc=1, 不得当绿)。
产物: eval/rover/r531/evidence/nc-grader-f3-r531.json
"""
import importlib.util, io, json, os, shutil, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r531")
TMP = "/tmp/r531_gate/nc-grader-f3"
OUT = os.path.join(R, "evidence", "nc-grader-f3-r531.json")

spec = importlib.util.spec_from_file_location("bf_r531", os.path.join(R, "build_fixture_r531.py"))
BF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BF)

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
       "HOME": TMP}


def parse_cases(stdout):
    for ln in reversed(stdout.strip().splitlines()):
        if ln.startswith("R531_CASES "):
            n, tot = ln.split()[1].split("/")
            return int(n), int(tot)
    return 0, 30


def run_pair(name, mutant):
    root = os.path.join(TMP, name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    if mutant != "__empty__":
        BF.oracle_tree(root, mutant)
    env = dict(ENV, HOME=root)
    pa = subprocess.run([sys.executable, "-I", "-B", os.path.join(R, "cases/run_cases_r531_math.py")],
                        cwd=root, capture_output=True, text=True, env=env, timeout=900)
    a_pass, a_tot = parse_cases(pa.stdout)
    gj = os.path.join(TMP, "%s-gradef3.json" % name)
    pb = subprocess.run([sys.executable, os.path.join(R, "grade_f3_r531.py"), "--dir", root, "--out", gj],
                        capture_output=True, text=True, env=env, timeout=900)
    b = json.load(io.open(gj, encoding="utf-8")) if os.path.isfile(gj) else {"passed": 0, "total": 30, "rc": 3}
    def _norm(line):
        name = line.split()[1]                       # 形如 modular/qr_count#00-hidden
        head, tail = name.split("#", 1)
        return "%s#%d" % (head.split("/")[-1], int(tail.split("-")[0]))

    a_fail = sorted(_norm(l) for l in pa.stdout.splitlines() if l.startswith("CASE ") and " FAIL" in l)
    b_fail = sorted("%s#%d" % (c["op"], c["i"]) for c in b.get("cases", []) if not c["ok"])
    align = (a_pass == b.get("passed")) and (set(a_fail) == set(b_fail))
    return {"name": name, "mutant": mutant, "cases_rc": pa.returncode, "cases_pass": a_pass,
            "cases_total": a_tot, "grader_rc": b.get("rc"), "grader_pass": b.get("passed"),
            "aligned": align, "drift": b.get("oracle_drift") or [],
            "cases_fail_sample": a_fail[:4], "grader_fail_sample": b_fail[:4]}


def main():
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(os.path.join(R, "evidence"), exist_ok=True)
    rows = [run_pair(n, m) for n, m in [("oracle", None), ("qr_offby1", "qr_offby1"),
                                        ("choose_nomod", "choose_nomod"), ("extra_text", "extra_text"),
                                        ("empty", "__empty__")]]
    pos = rows[0]
    ok_pos = (pos["cases_rc"] == 0 and pos["cases_pass"] == pos["cases_total"] == 30
              and pos["grader_rc"] == 0 and pos["grader_pass"] == 30)
    ok_neg = all((r["cases_rc"] != 0 and r["grader_rc"] != 0 and r["cases_pass"] < 30) for r in rows[1:])
    ok_align = all(r["aligned"] for r in rows)
    res = {"round": "R531", "family": "mathkit-multimodule-v1", "rows": rows,
           "positive_control_ok": ok_pos, "negative_controls_ok": ok_neg, "aligned": ok_align,
           "verdict": "PASS" if (ok_pos and ok_neg and ok_align) else "FAIL"}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    for r in rows:
        print("%-13s cases=%2d/%d rc=%s | grader=%2d rc=%s | aligned=%s" %
              (r["name"], r["cases_pass"], r["cases_total"], r["cases_rc"], r["grader_pass"],
               r["grader_rc"], r["aligned"]))
    print("NC_VERDICT=%s (pos=%s neg=%s align=%s)" % (res["verdict"], ok_pos, ok_neg, ok_align))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
