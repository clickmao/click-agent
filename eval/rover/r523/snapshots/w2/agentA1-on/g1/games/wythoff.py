"""Wythoff's game: subtract from one heap, or equal positive amounts from both.

Reports the lexicographically smallest winning move (i, j) on (a, b).
"""


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    # A position is losing iff (a, b) is a Wythoff pair: sorted pair equals
    # (floor(n*phi), floor(n*phi*phi)) for some n >= 0.
    lo, hi = (a, b) if a <= b else (b, a)
    phi = (1 + 5 ** 0.5) / 2
    n = int((hi - lo) / phi) if hi != lo else 0
    # Guard against floating point drift: check a couple of neighbours.
    for cand in (n - 1, n, n + 1, n + 2):
        if cand < 0:
            continue
        p = int(cand * phi)
        q = p + cand
        if (p, q) == (lo, hi):
            return 'LOSE'

    best = None
    # Option (i): take from one heap only.
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            nlo, nhi = (na, nb) if na <= nb else (nb, na)
            losing = False
            for cand in range(0, nhi + 1):
                p = int(cand * phi)
                q = p + cand
                if p > nlo:
                    break
                if (p, q) == (nlo, nhi):
                    losing = True
                    break
            if losing and (best is None or (i, j) < best):
                best = (i, j)

    return 'WIN %d %d' % best
