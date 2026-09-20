"""Wythoff's game: LOSE / WIN i j (lexicographically smallest winning move).

Move (i, j): remove i from pile 1 and j from pile 2, with i, j >= 0,
not both zero, and either a single pile (one of i, j is 0) or equal
amounts from both piles (i == j > 0).
"""


def is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if is_losing(a, b):
        return 'LOSE'

    best = None
    # i == j > 0: take the same positive amount from both piles
    for j in range(1, min(a, b) + 1):
        if is_losing(a - j, b - j):
            cand = (j, j)
            if best is None or cand < best:
                best = cand
    # j == 0, i > 0: take from pile 1 only
    for i in range(1, a + 1):
        if is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # i == 0, j > 0: take from pile 2 only
    for j in range(1, b + 1):
        if is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand

    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
