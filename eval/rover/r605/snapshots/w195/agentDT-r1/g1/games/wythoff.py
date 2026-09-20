def solve(text):
    a, b = [int(x) for x in text.split()[:2]]
    lose = set()
    sq5 = 5 ** 0.5
    for n in range(0, 30):
        an = int((n * (1 + sq5)) / 2 + 1e-9)
        bn = an + n
        if an > 25 and bn > 25:
            break
        lose.add((an, bn))
        lose.add((bn, an))
    if (a, b) in lose:
        return "LOSE"
    best = None
    for da in range(0, a + 1):
        for db in range(0, b + 1):
            if da == 0 and db == 0:
                continue
            na = a - da
            nb = b - db
            if (na, nb) in lose:
                cand = (da, db)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0], best[1])
