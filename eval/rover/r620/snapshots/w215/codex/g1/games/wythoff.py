"""Wythoff's game: solve(a, b) -> LOSE, or WIN i j with the lexicographically
smallest winning move (i taken from pile 1, j from pile 2)."""

COLD = None


def _cold_positions(limit):
    """All cold (P-)positions (x, y) with x, y <= limit.

    Cold positions are (floor(t*phi), floor(t*phi^2)) for t = 0, 1, 2, ...
    """
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    t = 0
    while True:
        p = int(t * phi)
        q = int(t * phi * phi)
        if p > limit and q > limit:
            break
        cold.add((p, q))
        cold.add((q, p))
        t += 1
    return cold


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    cold = _cold_positions(max(a, b) + 1)

    if (a, b) in cold:
        return "LOSE"

    # Try every legal move and keep the lexicographically smallest one
    # that leaves a cold position. A move takes i from pile 1 and j from
    # pile 2, where either i == 0, or j == 0, or i == j.
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in cold:
                best = (i, j) if best is None else min(best, (i, j))
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
