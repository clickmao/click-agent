"""Wythoff game: WIN i j (lexicographically smallest) or LOSE."""

PHI = (1 + 5 ** 0.5) / 2


def _is_lose_pair(x, y):
    if x > y:
        x, y = y, x
    # Beatty: losing positions are (floor(n*phi), floor(n*phi^2)) = (a_n, a_n + n)
    n = y - x
    an = int(n * PHI)
    for cand in (an - 2, an - 1, an, an + 1, an + 2):
        if cand < 0 or cand > x:
            continue
        if cand == x and cand + n == y and int(PHI * PHI * cand) == y and int(PHI * cand) == cand:
            return True
    return False


def _is_lose(x, y):
    if x > y:
        x, y = y, x
    n = y - x
    an = int(n * PHI)
    return 0 <= an and x == an and y == an + n and int(PHI * PHI * an) == y


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    # move type (i): remove i from one pile, j == 0
    for i in range(1, a + 1):
        if _is_lose(a - i, b):
            if best is None or (i, 0) < best:
                best = (i, 0)
    for j in range(1, b + 1):
        if _is_lose(a, b - j):
            if best is None or (0, j) < best:
                best = (0, j)
    # move type (ii): remove i from both piles
    for i in range(1, min(a, b) + 1):
        if _is_lose(a - i, b - i):
            if best is None or (i, i) < best:
                best = (i, i)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
