"""Wythoff's game: detect losing positions, else lexicographically smallest win."""


def _losing_positions(limit):
    """Return the set of P-positions (cold positions) with both coords <= limit."""
    lose = set()
    used = set()
    # P-positions are (floor(n*phi), floor(n*phi^2)) and its swap.
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        a = int(n * phi)
        b = int(n * phi * phi)
        n += 1
        if a > limit and b > limit:
            break
        if a <= limit and b <= limit:
            lose.add((a, b))
            lose.add((b, a))
        used.add(a)
        used.add(b)
    return lose


def solve(text: str) -> str:
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])

    limit = max(a, b)
    lose = _losing_positions(limit)

    if (a, b) in lose:
        return "LOSE"

    best = None
    # Option (i): take i from the first pile only.
    for i in range(a + 1):
        if i == 0:
            continue
        if (a - i, b) in lose:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # Option (i): take j from the second pile only.
    for j in range(b + 1):
        if j == 0:
            continue
        if (a, b - j) in lose:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # Option (ii): take the same t from both piles.
    for t in range(1, min(a, b) + 1):
        if (a - t, b - t) in lose:
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return "WIN %d %d" % best
