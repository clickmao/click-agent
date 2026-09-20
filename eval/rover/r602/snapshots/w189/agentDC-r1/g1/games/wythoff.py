"""Wythoff game: LOSE at cold positions, else lexicographically smallest winning move."""


def _losing(a, b):
    if a > b:
        a, b = b, a
    i = 0
    while True:
        ai = i * (1 + 5 ** 0.5) // 2
        ai = int((i * (1 + 5 ** 0.5)) // 2)
        bi = ai + i
        if ai > a:
            return False
        if ai == a and bi == b:
            return True
        i += 1


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    if _losing(a, b):
        return 'LOSE'

    # enumerate all legal moves, pick lexicographically smallest (i, j)
    best = None
    # single-pile moves: take from pile1 only (i>0, j=0) or pile2 only (i=0, j>0)
    for i in range(1, a + 1):
        if _losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if _losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # both piles by same amount
    for t in range(1, min(a, b) + 1):
        if _losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
