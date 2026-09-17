"""Wythoff 博弈: 必败点判定, 必胜时给字典序最小的取子对 (i, j)。

必败点 (a_n, b_n) = (floor(n*phi), floor(n*phi^2)) 及其交换。
必胜着法 = 一步使局面落到必败点; 取 (i, j) = (a-p, b-q), 其中
(i=0 单堆) 或 (j=0 单堆) 或 (i=j 等量双堆), 要求 i,j>=0 不同时为 0,
按 (i, j) 字典序最小。
"""
import math

_PHI = (1 + math.sqrt(5)) / 2


def _cold(a: int, b: int) -> bool:
    """(a, b) 是否为 Wythoff 必败点 (容忍浮点边界)。"""
    if a == 0 and b == 0:
        return True
    for x, y in ((a, b), (b, a)):
        if x == 0:
            continue
        n = int(math.floor((x + 1) / _PHI))
        for t in (n - 1, n, n + 1):
            if t < 0:
                continue
            if int(math.floor(t * _PHI)) == x and int(math.floor(t * _PHI * _PHI)) == y:
                return True
    return False


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _cold(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN %d %d" % best
