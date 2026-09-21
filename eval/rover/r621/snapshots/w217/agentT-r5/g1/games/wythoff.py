"""Wythoff 博弈: 字典序最小必胜着法。"""


def _losing(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    return x == int(d * (1 + 5 ** 0.5) / 2 + 1e-9)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not _losing(a - i, b - j):
                continue
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
