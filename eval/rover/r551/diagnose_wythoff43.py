#!/usr/bin/env python3
"""R551 附属定因器具: 对公开用例 `wythoff#43` (stdin `21 25`, 期望 `WIN 15 15`) 跑**各窗最终产物**,
按「着法合法性 + 落点必败性」机械分类。P 判据用**独立算式** `x == floor((y-x)*phi)` (Beatty 定理),
不复用被测产物自身代码 (非同源 oracle)。

用法: python3 eval/rover/r551/diagnose_wythoff43.py [--snapshots eval/rover/r551/snapshots] [--json out.json]
退出码: 0 = 全部窗分类成功 (无论类别是否 OK) / 3 = 输入缺失 fail-closed
"""
import argparse
import json
import math
import os
import subprocess
import sys

PHI = (1.0 + 5.0 ** 0.5) / 2.0
CASE_IN = "21 25\n"
CASE_EXP = "WIN 15 15"


def is_P(a, b):
    """必败点判定: (a,b) 是 Wythoff 必败点 <=> min == floor(|a-b| * phi) (Beatty)."""
    x, y = (a, b) if a <= b else (b, a)
    if x < 0 or y < 0:
        return False
    return x == int(math.floor((y - x) * PHI))


def classify(out, a=21, b=25):
    t = out.strip().split()
    if not t:
        return "CRASH_or_empty"
    if t[0] == "LOSE":
        return "OK_LOSE" if is_P(a, b) else "wrong_lose"
    if t[0] == "WIN":
        try:
            i, j = int(t[1]), int(t[2])
        except Exception:
            return "malformed"
        if i == 0 and j == 0:
            return "no_move"
        legal = (j == 0 and 0 < i <= a) or (i == 0 and 0 < j <= b) or (i > 0 and i == j and i <= min(a, b))
        if not legal:
            return "illegal_move"
        return "OK_WIN" if is_P(a - i, b - j) else "non_winning_move"
    return "malformed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots"))
    ap.add_argument("--json", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag-wythoff43.json"))
    a = ap.parse_args()
    rows = []
    if not os.path.isdir(a.snapshots):
        print("SNAPSHOTS_MISSING %s" % a.snapshots)
        return 3
    for win in sorted(os.listdir(a.snapshots)):
        wdir = os.path.join(a.snapshots, win)
        if not os.path.isdir(wdir):
            continue
        for arm in sorted(os.listdir(wdir)):
            cwd = os.path.join(wdir, arm, "g1")
            if not os.path.isdir(cwd):
                continue
            try:
                p = subprocess.run([sys.executable, "-B", "-m", "games", "wythoff"], input=CASE_IN,
                                   capture_output=True, text=True, cwd=cwd, timeout=60)
                out, rc, err = p.stdout.strip(), p.returncode, (p.stderr or "").strip()
            except subprocess.TimeoutExpired:
                out, rc, err = "", 124, "TIMEOUT"
            cls = classify(out)
            rows.append({"win": win, "arm": arm, "stdout": out, "cli_rc": rc,
                         "class": cls, "ok": (out == CASE_EXP), "stderr_tail": err[-200:]})
    for r in rows:
        print("%-4s %-22s out=%-14r rc=%-3d class=%-18s ok=%s" %
              (r["win"], r["arm"], r["stdout"], r["cli_rc"], r["class"], r["ok"]))
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump({"case": {"stdin": CASE_IN.strip(), "expected_stdout": CASE_EXP},
                   "oracle": "x == floor((y-x)*phi) (Beatty), 非同源", "rows": rows}, f,
                  ensure_ascii=False, indent=1)
    print("wrote %s (%d rows)" % (a.json, len(rows)))
    return 0 if rows else 3


if __name__ == "__main__":
    sys.exit(main())
