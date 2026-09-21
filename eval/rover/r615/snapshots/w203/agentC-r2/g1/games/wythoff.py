"""Wythoff game: losing position check; else lexicographically smallest winning move."""


def _losing(a, b):
    if a > b:
        a, b = b, a
    # Beatty sequences: (a, b) with b - a == d and a == floor(d * phi)
    d = b - a
    phi = (1 + 5 ** 0.5) / 2.0
    x = int(d * phi)
    for cand in (x - 1, x, x + 1):
        if cand >= 0 and int(cand * phi) + cand == b and cand == a and b - cand == d:
            return True
    return x == a


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    best = None
    # (i, j) with i from pile 1, j from pile 2
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
