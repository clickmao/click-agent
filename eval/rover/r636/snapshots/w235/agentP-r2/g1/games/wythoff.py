"""Wythoff 博弈: 必败点判定, 字典序最小的必胜着法。"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    root5 = 5 ** 0.5

    def is_losing(x, y):
        lo, hi = min(x, y), max(x, y)
        n = hi - lo
        return lo == int(n * (1 + root5) / 2)

    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        j = i
        if i > 0:
            na, nb = a - i, b - j
            if na >= 0 and nb >= 0 and is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
        na, nb = a - i, b
        if na >= 0 and na != a and is_losing(na, nb):
            if best is None or (i, 0) < best:
                best = (i, 0)
        na, nb = a, b - i
        if nb >= 0 and nb != b and is_losing(na, nb):
            if best is None or (0, i) < best:
                best = (0, i)
    return 'WIN %d %d' % best
