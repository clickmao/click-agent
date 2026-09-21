"""Wythoff 博弈: 必败点判定与字典序最小的必胜着法。"""


def _losing(a: int, b: int) -> bool:
    """(a, b) 是否为必败点 (P-position)。"""
    if a > b:
        a, b = b, a
    d = b - a
    x = int((d * (1 + 5 ** 0.5) / 2) + 1e-9)
    return a == x


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    a = int(tokens[0])
    b = int(tokens[1])

    if _losing(a, b):
        return "LOSE"

    best = None
    # 从任意一堆取正数颗 (单堆)
    for i in range(1, a + 1):
        cand = (i, 0)
        if best is None or cand < best:
            if _losing(a - i, b):
                best = cand
    for j in range(1, b + 1):
        cand = (0, j)
        if best is None or cand < best:
            if _losing(a, b - j):
                best = cand
    # 从两堆同时取相同正数颗
    for t in range(1, min(a, b) + 1):
        cand = (t, t)
        if best is None or cand < best:
            if _losing(a - t, b - t):
                best = cand

    i, j = best
    return "WIN %d %d" % (i, j)
