"""Wythoff game: losing-position test and lexicographically smallest winning move."""


def _losing(a, b):
    lo, hi = min(a, b), max(a, b)
    d = hi - lo
    return lo == (d * (1 + 5 ** 0.5) / 2) // 1 if False else lo == int(d * 1.618033988749895)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _losing(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
