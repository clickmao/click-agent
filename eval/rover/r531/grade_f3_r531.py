#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 F3 (mathkit-multimodule-v1) 冻结期独立判分器 (与前置器用例脚本非同源)。

三层非同源:
  ① 期望值由本文件**独立重算** (自己实现 5 个算子, 不 import eval/probe/tasks.py);
  ② 与前置器用例脚本的落盘列 `expected_stdout` (任务生成器 ref 路径) 逐例对撞,
     不一致 ⇒ 该例记 ORACLE_DRIFT 且整体 rc=3 (fail-closed, 不判绿);
  ③ 冻结只在仓内不可变快照上跑 (判分不读活目录)。

接口: --dir <快照根> --out <json>; rc 0=全对 / 1=有错例 / 3=输入缺失(用例文件/对撞失败)。
"""
import argparse, io, json, math, os, subprocess, sys
from fractions import Fraction
from heapq import heappush, heappop

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r531/cases/cases-r531-f3.json")


def qr_count(a, m):
    return sum(1 for x in range(m) if (x * x - a) % m == 0)


def choose(n, k, mod):
    return math.comb(n, k) % mod


def det_mod(matrix, mod):
    n = len(matrix)
    M = [[int(v) for v in row] for row in matrix]
    sign = 1
    prev = 1
    for i in range(n - 1):
        if M[i][i] == 0:
            for r in range(i + 1, n):
                if M[r][i] != 0:
                    M[i], M[r] = M[r], M[i]
                    sign = -sign
                    break
            else:
                return 0
        for r in range(i + 1, n):
            for c in range(i + 1, n):
                M[r][c] = (M[r][c] * M[i][i] - M[r][i] * M[i][c]) // prev
        prev = M[i][i]
        for r in range(i + 1, n):
            M[r][i] = 0
    return (sign * M[n - 1][n - 1]) % mod


def shortest(matrix, src, dst):
    n = len(matrix)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = heappop(pq)
        if d > dist[u]:
            continue
        if u == dst:
            break
        for v in range(n):
            w = matrix[u][v]
            if w and d + w < dist[v]:
                dist[v] = d + w
                heappush(pq, (d + w, v))
    return -1 if dist[dst] == INF else dist[dst]


def expect(red, blue, draw):
    fr = Fraction(draw * red, red + blue)
    return "%d/%d" % (fr.numerator, fr.denominator)


def independent(op, args):
    if op == "qr_count":
        return str(qr_count(args["a"], args["m"]))
    if op == "choose":
        return str(choose(args["n"], args["k"], args["mod"]))
    if op == "det":
        return str(det_mod(args["matrix"], args["mod"]))
    if op == "shortest":
        return str(shortest(args["matrix"], args["src"], args["dst"]))
    if op == "expect":
        return expect(args["red"], args["blue"], args["draw"])
    raise KeyError(op)


def run_cli(tree, op, args, timeout=60):
    # 契约 (承 R529 教训): 被测 CLI 用 `-B -m <pkg>` + PYTHONPATH=树根 启动;
    # **不得**加 `-I` —— 隔离模式会丢弃 PYTHONPATH ⇒ 恒 `No module named mathkit` (假红)。
    p = subprocess.run([sys.executable, "-B", "-m", "mathkit", op],
                       input=json.dumps(args), capture_output=True, text=True,
                       cwd=tree, timeout=timeout,
                       env=dict(os.environ, PYTHONPATH=tree, PYTHONDONTWRITEBYTECODE="1",
                                PYTHONHASHSEED="0"))
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases", default=CASES)
    a = ap.parse_args()
    if not os.path.isfile(a.cases):
        print("[致命] 缺用例文件 %s" % a.cases)
        return 3
    doc = json.load(io.open(a.cases, encoding="utf-8"))
    cases = doc["cases"] if isinstance(doc, dict) else doc
    rows, npass, drift = [], 0, []
    for idx, c in enumerate(cases):
        op, args = c["op"], c["args"]
        i = c.get("i", idx)
        want = c.get("expected_stdout")
        mine = independent(op, args)
        if want is not None and mine != want:
            drift.append("%s#%s(任务生成器=%r 独立重算=%r)" % (op, c.get("i"), want, mine))
            rows.append({"op": op, "i": i, "ok": False, "why": "ORACLE_DRIFT"})
            continue
        try:
            rc, out, err = run_cli(a.dir, op, args)
        except Exception as e:  # noqa: BLE001
            rows.append({"op": op, "i": i, "ok": False, "why": "EXC:%s" % e})
            continue
        got = out.strip()
        ok = (rc == 0 and got == mine)
        npass += 1 if ok else 0
        rows.append({"op": op, "i": i, "ok": ok, "expected": mine, "got": got[:60],
                     "rc": rc, "why": "" if ok else ("RC=%d" % rc if rc else "MISMATCH"),
                     "stderr": err.strip()[-120:] if (err and not ok) else ""})
    res = {"grader": "grade_f3_r531.py(独立实现)", "dir": a.dir, "passed": npass, "total": len(cases),
           "oracle_drift": drift, "cases": rows,
           "rc": 3 if drift else (0 if npass == len(cases) else 1)}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print("F3 独立判分: %d/%d rc=%d drift=%d" % (npass, len(cases), res["rc"], len(drift)))
    for r in rows:
        if not r["ok"]:
            print("  FAIL", r)
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
