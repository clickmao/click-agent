#!/usr/bin/env python3
"""Acceptance self-check for mathkit, run from the work root.

Drives every op through the real CLI entry (``python3 -m mathkit <op>``) with
JSON on stdin, byte-comparing stdout.  Includes the public cases plus
independent brute-force cross-checks and negative controls.

Run:  python3 -m mathkit.selftest
Exit: 0 = all PASS, non-zero = number of failures (also printed).
"""
import json
import random
import subprocess
import sys
from fractions import Fraction
from math import comb

FAIL = 0
PASS = 0


def run(op, payload):
    """Invoke the real CLI exactly as the grader does."""
    p = subprocess.run(
        [sys.executable, "-m", "mathkit", op],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout, p.stderr


def check(name, op, payload, expected):
    global FAIL, PASS
    rc, out, err = run(op, payload)
    ok = (rc == 0) and (out == expected) and (err == "")
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("%-28s FAIL  got=%r want=%r rc=%d err=%r"
              % (name, out, expected, rc, err))


# --- public cases (from the contract table) -------------------------------
check("public qr_count", "qr_count", {"a": 11, "m": 16}, "0")
check("public choose", "choose", {"n": 18, "k": 7, "mod": 97}, "8")
check("public det", "det",
      {"matrix": [[-2, 0], [-1, -6]], "mod": 101}, "12")
check("public shortest", "shortest",
      {"matrix": [[0, 0, 5, 1, 0], [0, 0, 1, 9, 6], [5, 1, 0, 0, 0],
                  [1, 9, 0, 0, 4], [0, 6, 0, 4, 0]], "src": 0, "dst": 4}, "5")
check("public expect", "expect", {"red": 1, "blue": 3, "draw": 3}, "3/4")

# --- qr_count: exhaustive across the declared domain ----------------------
for a in range(0, 13):
    for m in range(8, 17):
        want = sum(1 for x in range(m) if (x * x - a) % m == 0)
        check("qr_count a=%d m=%d" % (a, m), "qr_count",
              {"a": a, "m": m}, str(want))

# --- choose: exhaustive over the declared domain (0 <= k <= n) ------------
for mod in (97, 101, 1000003):
    for n in range(0, 41):
        for k in range(0, n + 1):
            want = str(comb(n, k) % mod)
            check("choose n=%d k=%d mod=%d" % (n, k, mod), "choose",
                  {"n": n, "k": k, "mod": mod}, want)

# --- choose: degenerate k > n must be honestly zero (not a crash) ---------
for n, k, mod in ((0, 1, 97), (3, 4, 101)):
    check("choose deg n=%d k=%d" % (n, k), "choose",
          {"n": n, "k": k, "mod": mod}, "0")


# --- det: brute force by permutation expansion vs Bareiss -----------------
def det_bruteforce(m):
    import itertools
    n = len(m)
    total = 0
    for perm in itertools.permutations(range(n)):
        inversions = sum(
            1 for i in range(n) for j in range(i + 1, n) if perm[i] > perm[j]
        )
        sign = -1 if inversions % 2 else 1
        prod = 1
        for i in range(n):
            prod *= m[i][perm[i]]
        total += sign * prod
    return total


random.seed(1234)
for trial in range(200):
    n = random.randint(2, 4)
    mat = [[random.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    mod = random.choice((97, 101))
    want = str(det_bruteforce(mat) % mod)
    check("det trial=%d n=%d mod=%d" % (trial, n, mod), "det",
          {"matrix": mat, "mod": mod}, want)

# --- shortest: Floyd-Warshall cross-check ---------------------------------
for trial in range(120):
    n = random.randint(4, 7)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w = random.choice([0, 0, 1, 2, 3, 5, 9])
            mat[i][j] = w
            mat[j][i] = w
    INF = float("inf")
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
        for j in range(n):
            if i != j and mat[i][j]:
                dist[i][j] = mat[i][j]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    src = random.randrange(n)
    dst = random.randrange(n)
    want = "-1" if dist[src][dst] == INF else str(dist[src][dst])
    check("shortest trial=%d n=%d" % (trial, n), "shortest",
          {"matrix": mat, "src": src, "dst": dst}, want)

# --- shortest: explicit unreachable case ----------------------------------
check("shortest unreachable", "shortest",
      {"matrix": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 1],
                  [0, 0, 1, 0]], "src": 0, "dst": 3}, "-1")

# --- expect: exact rational cross-check over the full domain --------------
for red in range(1, 7):
    for blue in range(1, 7):
        for draw in range(1, red + blue + 1):
            val = Fraction(draw * red, red + blue)
            want = "%d/%d" % (val.numerator, val.denominator)
            check("expect r=%d b=%d d=%d" % (red, blue, draw), "expect",
                  {"red": red, "blue": blue, "draw": draw}, want)

# --- expect: integer result must render as k/1 ----------------------------
check("expect integer", "expect", {"red": 3, "blue": 2, "draw": 5}, "3/1")
check("expect integer 2", "expect", {"red": 2, "blue": 4, "draw": 6}, "2/1")

# --- negative control: wrong answer must NOT be accepted ------------------
rc, out, err = run("qr_count", {"a": 11, "m": 16})
if out == "1":
    FAIL += 1
    print("negative-control            FAIL  (wrong answer accepted)")
else:
    PASS += 1
    print("negative-control            PASS  (wrong answer rejected: %r)" % out)

# --- contract: stdout has no trailing newline -----------------------------
for op, payload in (("expect", {"red": 3, "blue": 3, "draw": 3}),
                    ("qr_count", {"a": 11, "m": 16}),
                    ("det", {"matrix": [[1, 2], [3, 4]], "mod": 97})):
    rc, out, err = run(op, payload)
    if out.endswith("\n") or err != "":
        FAIL += 1
        print("no-trailing-newline %-8s FAIL out=%r err=%r" % (op, out, err))
    else:
        PASS += 1

print("TOTAL PASS = %d, FAILURES = %d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
