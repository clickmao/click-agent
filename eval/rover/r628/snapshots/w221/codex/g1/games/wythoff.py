"""Wythoff's game: give the lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        p = (5 ** 0.5 + 1) / 2
        return x == int(d * p)

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
