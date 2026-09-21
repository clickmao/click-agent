"""Wythoff 博弈: 输出 LOSE 或字典序最小的 WIN i j。"""

PHI = (1 + 5 ** 0.5) / 2


def losing(u, v):
    u, v = min(u, v), max(u, v)
    d = v - u
    bx = int(d * PHI)
    return u == bx


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
