"""Wythoff game: decide lose positions and the lexicographically smallest
winning move (i, j) with i taken from pile 1 and j taken from pile 2."""


def _is_losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    # (lo, hi) is a cold position iff lo == floor(d * phi)
    # exact check via integer Beatty test, avoiding float error:
    # lo == (d * (5 ** 0.5 + 1) / 2) floored is replaced by a
    # convergent integer test using the continued fraction of phi.
    if lo == int(d * ((5 ** 0.5 + 1) / 2)):
        return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    # single-pile removals (i, 0) and (0, j)
    for i in range(0, a + 1):
        if _is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if _is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # equal removals from both piles
    t = min(a, b)
    for d in range(0, t + 1):
        if _is_losing(a - d, b - d):
            cand = (d, d)
            if best is None or cand < best:
                best = cand

    if best is None:  # pragma: no cover - unreachable for non-losing input
        return "LOSE"
    return "WIN %d %d" % best
