"""Wythoff game: first player win/lose and lexicographically smallest move.

P-positions (a, b) with a <= b are (floor(n*phi), floor(n*phi*phi)) for n >= 0.
A position is losing iff it is one of those pairs (in either order).
From a winning position, the moves are: take i > 0 from pile 1 (i.e. -> (a-i, b)),
take j > 0 from pile 2 (-> (a, b-j)), or take t > 0 from both (-> (a-t, b-t)).
We enumerate all legal moves and pick the lexicographically smallest (i, j) that
leads to a losing position.
"""


def _is_losing(x: int, y: int) -> bool:
    a, b = (x, y) if x <= y else (y, x)
    n = b - a
    # a must equal floor(n * phi), b equal floor(n * phi * phi)
    phi = (1 + 5 ** 0.5) / 2
    k = int(n / phi)
    # check a small window around the candidate index to avoid float errors
    for cand in (k - 1, k, k + 1):
        if cand < 0:
            continue
        if int(cand * phi) == a and int(cand * phi * phi) == b:
            return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        j = i
        if i == 0:
            for jj in range(1, b + 1):
                if _is_losing(a, b - jj):
                    if best is None or (0, jj) < best:
                        best = (0, jj)
        else:
            if _is_losing(a - i, b - i):
                if best is None or (i, i) < best:
                    best = (i, i)
    for j in range(1, b + 1):
        if _is_losing(a, b - j):
            if best is None or (0, j) < best:
                best = (0, j)
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            if best is None or (i, 0) < best:
                best = (i, 0)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
