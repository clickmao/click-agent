"""Wythoff's game: losing position test and lexicographically minimal move."""

MAX = 25


def _build():
    lose = set()
    seen_a = set()
    seen_b = set()
    pairs = []
    d = 0
    while True:
        a = d
        while a in seen_a:
            a += 1
        b = a + d
        if a > MAX:
            break
        if b > MAX:
            break
        pairs.append((a, b))
        seen_a.add(a)
        seen_a.add(b)
        seen_b.add(a)
        seen_b.add(b)
        d += 1
    for a, b in pairs:
        lose.add((a, b))
        lose.add((b, a))
    return lose


LOSE = _build()


def solve(text):
    a, b = (int(x) for x in text.split())
    if (a, b) in LOSE:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in LOSE:
                if best is None:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
