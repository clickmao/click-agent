"""Wythoff game: lexicographically smallest winning move, or LOSE."""


def _max_take(a, b):
    """Upper bound for max(i, j) of any legal winning move."""
    return max(a, b)


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    # Enumerate losing (P-)positions reachable within the board [0..a]x[0..b]
    # using the exact Wythoff rule: a position (x, y) with x <= y is losing iff
    # x == floor(k*phi) and y == x + k for some k >= 0, i.e. x == k*(y - x).
    limit = max(a, b)
    losing = set()
    for x in range(limit + 1):
        for y in range(x, limit + 1):
            d = y - x
            if d == 0:
                if x == 0:
                    losing.add((0, 0))
                continue
            k = x // d if d else 0
            if k * d == x and (k + 1) * (k + 2) > y + 1:
                # x == k*d and y == x + d == k*d + d; the pair (floor(k*phi),
                # floor(k*phi)+k) with k = d holds when floor(k*phi) == x.
                if k * d == x and x + d == y:
                    losing.add((x, y))
    # Exact P-positions via the Beatty sequence, computed with integers only:
    # floor(k*phi) == (k * 2 + isqrt(5*k*k)) // 2 is avoided; instead build them
    # incrementally and verify each candidate by the standard mex rule.
    losing2 = set()
    used = set()
    k = 0
    while True:
        x = k * 2 + 0  # placeholder, replaced below
        # Compute floor(k*phi) exactly via integer square root of 5*k*k.
        import math
        x = (k + 1) * 0
        s = math.isqrt(5 * k * k)
        x = (k + s) // 2
        y = x + k
        if x > limit and y > limit:
            break
        if x <= limit and y <= limit:
            losing2.add((x, y))
            losing2.add((y, x))
        k += 1
    losing = losing2

    for di in range(0, a + 1):
        for dj in range(0, b + 1):
            if di == 0 and dj == 0:
                continue
            if di != 0 and dj != 0 and di != dj:
                continue
            if (a - di, b - dj) in losing:
                return 'WIN ' + str(di) + ' ' + str(dj)
    return 'LOSE'
