"""Wythoff's game: report the lexicographically smallest winning move."""


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    # Cold (losing) positions: (floor(n*phi), floor(n*phi^2)) and the mirror.
    cold = set()
    n = 0
    while True:
        x = (n * 1618033988749895) // 1000000000000000
        y = (n * 2618033988749895) // 1000000000000000
        if x > 25 and y > 25:
            break
        cold.add((x, y))
        cold.add((y, x))
        n += 1
    if (a, b) in cold:
        return "LOSE"
    best = None
    # (i) take from a single pile
    for i in range(0, a + 1):
        if i > 0 and (a - i, b) in cold:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if j > 0 and (a, b - j) in cold:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (ii) take the same positive amount from both piles
    limit = min(a, b)
    for t in range(1, limit + 1):
        if (a - t, b - t) in cold:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0], best[1])
