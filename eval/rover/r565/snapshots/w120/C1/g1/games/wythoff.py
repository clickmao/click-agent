"""Wythoff's game: find lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * (1 + 5 ** 0.5) / 2)

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == 0 or j == 0 or i == j) and losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    i, j = best
    return "WIN %d %d" % (i, j)
