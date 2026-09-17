"""mathkit 自检：公开用例 + 交叉验证 + 负向控制。运行: python3 selftest_mathkit.py"""
import json
import subprocess
import sys
from fractions import Fraction
from itertools import combinations
from math import comb
from random import Random

REPO = None  # 工作根取当前目录


def run(op, payload):
    p = subprocess.run(
        [sys.executable, "-m", "mathkit", op],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout, p.stderr


fails = []


def check(name, got, exp, rc=0, err=""):
    ok = (got == exp) and (rc == 0) and (err == "")
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={got!r} exp={exp!r} rc={rc} err={err!r}")
    if not ok:
        fails.append(name)


# ---- 公开用例（逐字节比对） ----
check("qr_count public", *run("qr_count", {"a": 11, "m": 16})[:1], exp="0") if False else None
rc, out, err = run("qr_count", {"a": 11, "m": 16})
check("qr_count public", out, "0", rc, err)

rc, out, err = run("choose", {"n": 18, "k": 7, "mod": 97})
check("choose public", out, "8", rc, err)

rc, out, err = run("det", {"matrix": [[-2, 0], [-1, -6]], "mod": 101})
check("det public", out, "12", rc, err)

rc, out, err = run("shortest", {"matrix": [[0, 0, 5, 1, 0], [0, 0, 1, 9, 6], [5, 1, 0, 0, 0], [1, 9, 0, 0, 4], [0, 6, 0, 4, 0]], "src": 0, "dst": 4})
check("shortest public", out, "5", rc, err)

rc, out, err = run("expect", {"red": 1, "blue": 3, "draw": 3})
check("expect public", out, "3/4", rc, err)

# ---- 交叉验证：qr_count 暴力 vs 独立枚举 ----
rng = Random(1234)
for _ in range(40):
    a = rng.randint(0, 12)
    m = rng.randint(8, 16)
    exp = sum(1 for x in range(m) if (x * x - a) % m == 0)
    rc, out, err = run("qr_count", {"a": a, "m": m})
    if out != str(exp) or rc != 0 or err != "":
        print(f"[FAIL] qr_count rand a={a} m={m} got={out!r} exp={exp}")
        fails.append("qr_count rand")
        break
else:
    print("[PASS] qr_count 40 random cases")

# ---- 交叉验证：choose vs math.comb ----
for _ in range(40):
    n = rng.randint(0, 40)
    k = rng.randint(0, n)
    mod = rng.choice([97, 101, 1000003])
    exp = comb(n, k) % mod
    rc, out, err = run("choose", {"n": n, "k": k, "mod": mod})
    if out != str(exp) or rc != 0 or err != "":
        print(f"[FAIL] choose n={n} k={k} mod={mod} got={out!r} exp={exp}")
        fails.append("choose rand")
        break
else:
    print("[PASS] choose 40 random cases")

# ---- 交叉验证：det vs 独立递归展开 ----
def det_rec(mat):
    n = len(mat)
    if n == 1:
        return mat[0][0]
    if n == 2:
        return mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]
    tot = 0
    for c in range(n):
        minor = [[mat[r][cc] for cc in range(n) if cc != c] for r in range(1, n)]
        tot += ((-1) ** c) * mat[0][c] * det_rec(minor)
    return tot

for _ in range(30):
    n = rng.randint(2, 4)
    mat = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    mod = rng.choice([97, 101])
    exp = det_rec(mat) % mod
    rc, out, err = run("det", {"matrix": mat, "mod": mod})
    if out != str(exp) or rc != 0 or err != "":
        print(f"[FAIL] det mat={mat} mod={mod} got={out!r} exp={exp}")
        fails.append("det rand")
        break
else:
    print("[PASS] det 30 random cases")

# ---- 交叉验证：shortest vs Floyd-Warshall ----
for _ in range(30):
    n = rng.randint(4, 7)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < 0.5:
                w = rng.randint(1, 9)
                mat[i][j] = w
                mat[j][i] = w
    src = rng.randrange(n)
    dst = rng.randrange(n)
    INF = float("inf")
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
        for j in range(n):
            if mat[i][j]:
                d[i][j] = mat[i][j]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    exp = "-1" if d[src][dst] == INF else str(d[src][dst])
    rc, out, err = run("shortest", {"matrix": mat, "src": src, "dst": dst})
    if out != exp or rc != 0 or err != "":
        print(f"[FAIL] shortest mat={mat} src={src} dst={dst} got={out!r} exp={exp}")
        fails.append("shortest rand")
        break
else:
    print("[PASS] shortest 30 random cases")

# ---- 不可达显式用例（负向控制路径） ----
rc, out, err = run("shortest", {"matrix": [[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 2], [0, 0, 2, 0]], "src": 0, "dst": 3})
check("shortest unreachable", out, "-1", rc, err)

# ---- 交叉验证：expect vs 枚举超几何 ----
for _ in range(30):
    red = rng.randint(1, 6)
    blue = rng.randint(1, 6)
    draw = rng.randint(1, red + blue)
    total = red + blue
    # 期望 = sum_k k * C(red,k)*C(blue,draw-k)/C(total,draw)
    e = Fraction(0)
    for k in range(0, min(red, draw) + 1):
        b = draw - k
        if 0 <= b <= blue:
            e += Fraction(k * comb(red, k) * comb(blue, b), comb(total, draw))
    exp = f"{e.numerator}/{e.denominator}"
    rc, out, err = run("expect", {"red": red, "blue": blue, "draw": draw})
    if out != exp or rc != 0 or err != "":
        print(f"[FAIL] expect r={red} b={blue} d={draw} got={out!r} exp={exp}")
        fails.append("expect rand")
        break
else:
    print("[PASS] expect 30 random cases")

# ---- 结构完整性：包内文件均存在 ----
import os
for f in ["__init__.py", "modular.py", "linear.py", "graphs.py", "prob.py", "__main__.py"]:
    if not os.path.isfile(os.path.join("mathkit", f)):
        print(f"[FAIL] missing mathkit/{f}")
        fails.append("missing " + f)
else:
    print("[PASS] all package files present")

print("RESULT:", "PASS" if not fails else f"FAIL({len(fails)}): {fails}")
sys.exit(0 if not fails else 1)
