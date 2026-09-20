"""Wythoff's game: determine the outcome and lexicographically smallest move."""

MAXV = 25
PHI = (1 + 5 ** 0.5) / 2


def _cold_points(limit):
    """Losing (P) positions whose coordinates are both at most ``limit``.

    The k-th cold pair is (floor(k*phi), floor(k*phi) + k), k >= 1; the
    pair (0, 0) and the reflections of all pairs are cold as well.
    """
    cold = {(0, 0)}
    k = 1
    while True:
        a = int(k * PHI)
        b = a + k
        if a > limit:
            break
        if b <= limit:
            cold.add((a, b))
            cold.add((b, a))
        k += 1
    return cold


COLD = _cold_points(MAXV)


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])
    if (a, b) in COLD:
        return 'LOSE'
    # Enumerate every legal winning move, then take the lexicographically
    # smallest (i, j) pair.  i == j == 0 is not a legal move.
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in COLD:
                moves.append((i, j))
    i, j = min(moves)
    return 'WIN %d %d' % (i, j)
