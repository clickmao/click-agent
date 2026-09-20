def solve(text):
    a, b = map(int, text.split())
    x, y = (a, b) if a <= b else (b, a)
    cand = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            if i > 0 and j == 0:
                pass
            if i == 0 and j > 0:
                pass
            na, nb = a - i, b - j
            p, q = (na, nb) if na <= nb else (nb, na)
            d = q - p
            if p == int(d * 1.618033988749895) and (p == 0 or d >= 1):
                cand = (i, j)
                break
        if cand is not None:
            break
    if cand is None:
        return 'LOSE'
    return 'WIN ' + str(cand[0]) + ' ' + str(cand[1])
