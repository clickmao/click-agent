"""Wythoff game: losing positions = (floor(n*phi), floor(n*phi*phi));
report the lexicographically smallest winning move."""

PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _lower(n):
    return int(n * PHI)


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    if a < 1:
        return False
    n = _lower(a)
    return _lower(n) == a and _lower(n + 1) == b


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        j = i
        if j > b:
            break
        na, nb = a - i, b - j
        if i == 0 and j == 0:
            continue
        if _is_losing(na, nb):
            best = (i, j)
            break
    if best is None:
        for i in range(1, a + 1):
            na, nb = a - i, b
            if _is_losing(na, nb):
                best = (i, 0)
                break
    if best is None:
        for j in range(1, b + 1):
            na, nb = a, b - j
            if _is_losing(na, nb):
                best = (0, j)
                break
    i, j = best
    return "WIN %d %d" % (i, j)
