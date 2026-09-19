"""Wythoff: a b. LOSE if losing position else WIN i j lexicographically smallest winning move.

Cold (P) positions check: difference d = b - a, P iff a == floor(d * phi).
"""


PHI = (1 + 5 ** 0.5) / 2


def _is_cold(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * PHI)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_cold(a, b):
        return 'LOSE'
    X, Y = a, b
    zero_zero = set()
    zero_zero.add((0, 0))
    candidates = set()
    for i in range(1, X + 1):
        candidates.add((i, 0))
    for j in range(1, Y + 1):
        candidates.add((0, j))
    for d in range(1, min(X, Y) + 1):
        candidates.add((d, d))
    best = None
    for (i, j) in candidates:
        na, nb = X - i, Y - j
        if _is_cold(na, nb):
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
