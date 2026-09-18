def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])
    lose = set()
    for x in range(1, a + 1):
        for y in range(1, b + 1):
            ok = False
            for i in range(0, x + 1):
                if (x - i, y) in lose or (x - i, y) in lose:
                    pass
                if i > 0 and (x - i, y) in lose:
                    ok = True
                    break
                if i == 0 and (x, y) in lose:
                    ok = True
                    break
            if not ok:
                for j in range(1, y + 1):
                    if (x, y - j) in lose:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(x, y) + 1):
                    if (x - d, y - d) in lose:
                        ok = True
                        break
            if not ok:
                lose.add((x, y))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            t = 0 if (i > 0 and j > 0) else 1
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j == 0:
                pass
            if i == 0 and j > 0:
                pass
            na, nb = a - i, b - j
            if (na, nb) in lose or na == 0 and nb == 0:
                if na == 0 and nb == 0:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
                elif (na, nb) in lose:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
