"""Wythoff's game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    # P-positions (cold positions): (floor(n*phi), floor(n*phi^2)).
    phi = (1 + 5 ** 0.5) / 2
    lo, hi = min(a, b), max(a, b)

    def is_cold(x, y):
        if x > y:
            x, y = y, x
        n = int(y - x)
        if n < 0:
            return False
        return int(n * phi) == x and int(n * phi * phi) == y

    if is_cold(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    return "WIN %d %d" % best
