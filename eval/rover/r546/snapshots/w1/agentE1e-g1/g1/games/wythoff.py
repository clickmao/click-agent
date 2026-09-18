def solve(text: str) -> str:
    vals = text.split()
    a = int(vals[0])
    b = int(vals[1])
    # losing (cold) positions: (floor(n*phi), floor(n*phi*phi))
    phi = (1 + 5 ** 0.5) / 2
    i = 0
    while True:
        c = int(i * phi)
        d = c + i
        if c > 25 and d > 25:
            break
        if c == a and d == b:
            return 'LOSE'
        if c == b and d == a:
            return 'LOSE'
        i += 1
    best = None
    for di in range(0, a + 1):
        for dj in range(0, b + 1):
            if di == 0 and dj == 0:
                continue
            if di != 0 and dj != 0 and di != dj:
                continue
            na = a - di
            nb = b - dj
            if (na == 0 and nb == 0) or (1 <= na <= 25 and 1 <= nb <= 25):
                pass
            j = 0
            is_lose = False
            while True:
                c = int(j * phi)
                d = c + j
                if c > 25 and d > 25:
                    break
                if (c == na and d == nb) or (c == nb and d == na):
                    is_lose = True
                    break
                j += 1
            if is_lose or (na == 0 and nb == 0):
                cand = (di, dj)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
