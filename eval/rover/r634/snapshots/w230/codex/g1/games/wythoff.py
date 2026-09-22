"""Wythoff's game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split())

    def is_losing(x, y):
        # Cold positions are (floor(phi*n), floor(phi^2*n)).
        phi = (1 + 5 ** 0.5) / 2
        n = int((min(x, y)) / phi + 1e-9)
        # guard against floating point edge cases
        for cand in range(max(0, n - 2), n + 3):
            lo = int(cand * phi)
            hi = int(cand * phi * phi)
            if (x, y) == (lo, hi) or (x, y) == (hi, lo):
                return True
        return False

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j):
                if not is_losing(a - i, b - j):
                    continue
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
