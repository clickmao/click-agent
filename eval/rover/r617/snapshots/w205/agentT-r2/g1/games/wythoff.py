"""Wythoff game: losing positions and lexicographically smallest winning move.

Losing positions satisfy (x, y) = (floor(n*phi), floor(n*phi^2)), i.e.
y - x == n and x == floor(n*phi).  A position is losing iff, after
orientation x <= y, x == floor((y - x) * phi).
"""

PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _is_losing(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    n = y - x
    return x == int(n * PHI)


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    # Winning moves: subtract from pile 1 only, pile 2 only, or both equally.
    # Enumerate in lexicographic order of the resulting move counts (i, j).
    best_i = None
    best_j = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # legal: take from one pile only, or the same number from both
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                best_i, best_j = i, j
                break
        if best_i is not None:
            break
    if best_i is None:
        return "LOSE"
    return "WIN %d %d" % (best_i, best_j)
