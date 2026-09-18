"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

stdin: 一行两个整数 a b。
输出 'LOSE' 或 'WIN i j'（i,j>=0 且不同时为 0）。
"""


def _is_losing(x: int, y: int) -> bool:
    # 必败点: (floor(k*phi), floor(k*phi)+k)
    if x > y:
        x, y = y, x
    k = y - x
    t = (k * (1 + 5 ** 0.5)) / 2.0
    return x == int(t)


def solve(text: str) -> str:
    lines = text.split("\n")
    a, b = map(int, lines[0].split())
    if _is_losing(a, b):
        return "LOSE"
    best = None
    moves = []
    # 只从一堆取
    for i in range(0, a + 1):
        moves.append((i, 0))
    for j in range(0, b + 1):
        moves.append((0, j))
    # 两堆同时取相同数
    d = min(a, b)
    for t in range(1, d + 1):
        moves.append((t, t))
    for i, j in moves:
        if i == 0 and j == 0:
            continue
        if i > a or j > b:
            continue
        if _is_losing(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
