"""Wythoff game: remove any positive from one pile, or equal positive from both."""


def _lose(a, b):
    x, y = (a, b) if a <= b else (b, a)
    cx, cy = 0, 0
    i = 0
    while cy <= 25:
        if cx == x and cy == y:
            return True
        i += 1
        cx = cy + 1
        cy = cx + i
    return False


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _lose(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            if _lose(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
        if best is not None and best[0] == i:
            break
    return "WIN %d %d" % best
