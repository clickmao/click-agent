"""Wythoff game: take from one pile, or equal amounts from both."""


def _is_losing(a, b):
    """(a, b) is a P-position iff {a, b} == {floor(m*phi), floor(m*phi^2)}."""
    x, y = (a, b) if a <= b else (b, a)
    m = y - x
    if m < 0:
        return False
    # floor(m * (1 + sqrt(5)) / 2) without floats: smallest t with t*t <= m*m + m
    lo, hi = 0, m + 1
    while lo < hi:
        mid = (lo + hi) // 2
        if mid * mid <= m * m + m:
            lo = mid + 1
        else:
            hi = mid
    return x == lo - 1


def solve(text):
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    a, b = (int(x) for x in lines[0].split())
    if _is_losing(a, b):
        return "LOSE"
    moves = [(i, 0) for i in range(1, a + 1)]
    moves += [(0, j) for j in range(1, b + 1)]
    t = min(a, b)
    moves += [(d, d) for d in range(1, t + 1)]
    moves.sort()
    for i, j in moves:
        if _is_losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
