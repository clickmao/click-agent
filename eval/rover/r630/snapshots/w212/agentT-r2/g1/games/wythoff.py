"""Wythoff's game."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    def cold(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        # cold positions: (floor(d*phi), floor(d*phi)+d)
        phi = (1 + 5 ** 0.5) / 2
        t = int(d * phi)
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and cand >= 0 and (lo, hi) == (cand, cand + d):
                return True
        return False

    if cold(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if cold(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
