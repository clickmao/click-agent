"""Wythoff game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    lines = text.split()
    it = iter(lines)
    a = int(next(it))
    b = int(next(it))

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        ax = (5 ** 0.5 + 1) / 2
        cx = int(ax * d)
        for cand in (cx - 1, cx, cx + 1):
            if cand >= 0 and cand + d == y and cand == x:
                return True
        return False

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return "WIN %d %d" % (i, j)
