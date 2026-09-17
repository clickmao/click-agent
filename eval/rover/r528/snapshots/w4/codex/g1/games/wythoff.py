"""Wythoff's game: detect losing positions and give lexicographically smallest win."""


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    # Beatty sequences: losing positions are (floor(m*phi), floor(m*phi^2))
    # with b - a = m.
    d = b - a
    if d < 0:
        return False
    import math
    phi = (1 + math.sqrt(5)) / 2
    lo = int(math.floor(d * phi))
    return a == lo and b == lo + d


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # moves: single-pile or equal-from-both
            if i == 0 or j == 0 or i == j:
                if _is_losing(a - i, b - j):
                    if best is None:
                        best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
