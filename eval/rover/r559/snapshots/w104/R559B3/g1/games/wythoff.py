def solve(text):
    a, b = map(int, text.split()[0:2])

    maxn = max(a, b) + 1
    losing = []
    m = 0
    while True:
        x = (m * (1 + 5 ** 0.5) / 2)
        xi = int(x)
        if xi > maxn or xi + m > maxn + 1:
            break
        losing.append((xi, xi + m))
        m += 1

    losing_firsts = set(p[0] for p in losing)

    is_lose = False
    for p, q in losing:
        if (p == a and q == b) or (p == b and q == a):
            is_lose = True
            break

    if is_lose:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        jmax = b if i == 0 else (b - i)
        if i == 0:
            js = range(1, b + 1)
        else:
            js = [i] if b >= i else []
        for j in js:
            if j > b:
                continue
            if i == j:
                na, nb = a - i, b - i
            elif j == 0:
                na, nb = a - i, b
            else:
                na, nb = a - i, b - j
            na, nb = (na, nb) if na <= nb else (nb, na)
            lose = False
            for p, q in losing:
                if (p == na and q == nb):
                    lose = True
                    break
            if lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
