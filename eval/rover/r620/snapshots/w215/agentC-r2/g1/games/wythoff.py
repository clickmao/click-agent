"""Wythoff 博弈: 必败点判定与字典序最小的必胜着法。

输入: 一行两个整数 a b。
输出: 先手必败 => 'LOSE'; 否则 'WIN i j' (字典序最小, i/j 为各堆取走颗数)。
"""


def _xy(a1, b1):
    return (a1, b1) if a1 <= b1 else (b1, a1)


def _is_losing(a1, b1):
    lo, hi = _xy(a1, b1)
    d = hi - lo
    lo_expect = int(d * (1 + 5 ** 0.5) / 2.0)
    for cand in (lo_expect - 1, lo_expect, lo_expect + 1):
        if cand < 0:
            continue
        if cand == lo and cand + d == hi:
            return True
    return False


def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return "WIN %d %d" % (i, j)
