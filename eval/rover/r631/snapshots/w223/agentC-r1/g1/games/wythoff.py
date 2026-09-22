"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

入参 text 为完整 stdin 文本，返回应当写出的 stdout 文本（末尾不带换行）。
"""


def _cold(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    tok = text.split()
    a, b = int(tok[0]), int(tok[1])

    if _cold(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            if _cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
