"""Wythoff game: two piles a, b.
Moves: (i) remove any positive number from one pile, or
(ii) remove the same positive number from both piles.
Last stone wins. Output 'LOSE' for P-positions, else 'WIN i j' with the
lexicographically smallest winning move (compare i first, then j;
i, j >= 0, not both zero).
"""


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    n = max(a, b)

    # P-positions: sorted pairs of the form (floor(t*phi), floor(t*phi^2))
    import math
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    losing = set()
    t = 1
    while True:
        x = int(math.floor(t * phi))
        y = int(math.floor(t * phi * phi))
        if x > n or y > n:
            break
        losing.add((x, y))
        t += 1

    def is_losing(p: int, q: int) -> bool:
        lo, hi = (p, q) if p <= q else (q, p)
        return (lo, hi) in losing

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ai, bj = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue  # two-pile moves require equal amounts
            if is_losing(ai, bj):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
