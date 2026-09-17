def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])
    # compute losing positions up to 25
    lose = set()
    for x in range(0, 26):
        for y in range(x, 26):
            ok = True
            for (p, q) in lose:
                if p == x or q == y or (q - p) == (y - x):
                    ok = False
                    break
            if ok:
                lose.add((x, y))
    if (a, b) in lose or (b, a) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in lose or (nb, na) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
