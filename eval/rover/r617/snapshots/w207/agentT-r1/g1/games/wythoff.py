"""Wythoff game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x, y):
        if x == 0 and y == 0:
            return True
        if x == 0 or y == 0:
            return False
        lo, hi = (x, y) if x <= y else (y, x)
        d = hi - lo
        t = (5 ** 0.5 + 1) / 2
        eq = int(d * t)
        for cand in (eq - 1, eq, eq + 1):
            if cand >= 0 and cand == lo and cand + d == hi:
                return True
        return False

    if losing(a, b):
        return "LOSE"
    cands = []
    for d in range(1, b + 1):
        if a - d >= 0:
            cands.append((d, d))
    for i in range(1, a + 1):
        cands.append((i, 0))
    for j in range(1, b + 1):
        cands.append((0, j))
    cands.sort()
    for i, j in cands:
        if losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
