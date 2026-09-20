"""Wythoff 博弈: 判定必败点并给出字典序最小的必胜着法。

solve(text) 读入: 一行两个整数 a b。
输出 'LOSE' 或 'WIN i j' (i,j>=0, 不同时为 0; 按 (i,j) 字典序最小),
末尾不带换行。
"""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    n = max(a, b)
    lose = set()
    for x in range(n + 1):
        for y in range(x, n + 1):
            ok = True
            for (u, v) in lose:
                if (u == x and v == y) or (u == y and v == x):
                    ok = False
                    break
                if u - x == v - y or u - y == v - x:
                    ok = False
                    break
            if ok:
                lose.add((x, y))
    for (u, v) in lose:
        if (u == a and v == b) or (u == b and v == a):
            return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                na, nb = a - i, b - j
            else:
                continue
            key = (i, j)
            if best is None or key < best:
                lo, hi = min(na, nb), max(na, nb)
                if (lo, hi) in lose:
                    best = key
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            key = (i, j)
            if best is None or key < best:
                lo, hi = min(na, nb), max(na, nb)
                if (lo, hi) in lose:
                    best = key
    return 'WIN %d %d' % best
