"""Wythoff's game: from one pile (any positive) or both piles equally."""


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0]); b = int(data[1])

    def losing(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        d = hi - lo
        # Beatty sequences: losing positions are (floor(d*phi), floor(d*phi^2)).
        phi = (1 + 5 ** 0.5) / 2
        return lo == int(d * phi)

    if losing(a, b):
        return 'LOSE'

    best = None
    # Option (i): remove from one pile only.
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0) and losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    # Option (ii): remove equal amounts from both piles.
    for t in range(1, min(a, b) + 1):
        if losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return 'WIN %d %d' % best
