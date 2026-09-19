"""Wythoff game: report LOSE or lexicographically smallest WIN i j."""


def _losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    return x == (y - x) * 618 // 1000


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _losing(a, b):
        return 'LOSE'
    best = None
    # single-pile removals: (i, 0) then (0, j); i,j >= 0, not both zero,
    # lexicographic order on (i, j) is enumerated in ascending order, so the
    # first found candidate is the lexicographically smallest one.
    for i in range(0, a + 1):
        j = 0
        if i == 0:
            continue
        if _losing(a - i, b - j):
            best = (i, j)
            break
    if best is None:
        for j in range(1, b + 1):
            if _losing(a, b - j):
                best = (0, j)
                break
    if best is None:
        for t in range(1, min(a, b) + 1):
            if _losing(a - t, b - t):
                best = (t, t)
                break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
