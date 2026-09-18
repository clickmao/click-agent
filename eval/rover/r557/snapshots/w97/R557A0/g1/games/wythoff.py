def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    # LOSE positions: (floor(k*phi), floor(k*phi*phi)) and swap; phi=(1+sqrt5)/2

    is_lose = False
    for k in range(0, 30):
        f = int(k * ((1 + 5 ** 0.5) / 2))
        g = f + k
        if (a == f and b == g) or (a == g and b == f):
            is_lose = True
            break
    if is_lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i > a or j > b:
                continue
            na, nb = a - i, b - j
            is_lose2 = False
            for k in range(0, 30):
                f = int(k * ((1 + 5 ** 0.5) / 2))
                g = f + k
                if (na == f and nb == g) or (na == g and nb == f):
                    is_lose2 = True
                    break
            if is_lose2:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
