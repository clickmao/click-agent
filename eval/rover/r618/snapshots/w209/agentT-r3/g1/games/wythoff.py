"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * ((5 ** 0.5 + 1) / 2) + 1e-12)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if (i == 0 and j == 0) or (i != 0 and j != 0 and i != j):
                continue
            na, nb = a - i, b - j
            if not _is_lose(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
