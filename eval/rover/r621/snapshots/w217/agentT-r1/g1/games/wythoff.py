"""Wythoff 博弈: LOSE / WIN i j (字典序最小的必胜着法)。

输入: 一行两个整数 a b。
"""


def _losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    phi = (1 + 5 ** 0.5) / 2
    return lo == int(d * phi)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    moves = []
    for i in range(0, a + 1):
        moves.append((i, 0))
    for j in range(0, b + 1):
        moves.append((0, j))
    t = min(a, b)
    for d in range(1, t + 1):
        moves.append((d, d))

    best = None
    for i, j in moves:
        if i == 0 and j == 0:
            continue
        if i <= a and j <= b and _losing(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
