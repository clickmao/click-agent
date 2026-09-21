"""Wythoff's game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    def losing(x, y):
        lo, hi = min(x, y), max(x, y)
        return lo == int((hi - lo) * ((5 ** 0.5 + 1) / 2))

    if losing(a, b):
        return "LOSE"

    best = None
    # Move (i) from a single pile.
    for i in range(0, a + 1):
        for j in (0,) if i else range(1, b + 1):
            if i == 0 and j == 0:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    # Move (ii) from both piles equally.
    for t in range(1, min(a, b) + 1):
        if losing(a - t, b - t):
            if best is None or (t, t) < best:
                best = (t, t)

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
