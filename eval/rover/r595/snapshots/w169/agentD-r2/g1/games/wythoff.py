def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    cap = 25
    lose = set()
    cnt = 0
    n = 0
    while cnt <= 64:
        x = n + 1
        y = x + n
        if x > cap and y > cap:
            break
        lose.add((x, y))
        lose.add((y, x))
        cnt += 1
        n += 1
    if (a, b) in lose:
        return 'LOSE'
    best = None
    i = 0
    while i <= a:
        j = 0
        while j <= b:
            if i == 0 and j == 0:
                j += 1
                continue
            if i > 0 and j > 0 and i != j:
                j += 1
                continue
            na = a - i
            nb = b - j
            if (na, nb) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
            j += 1
        i += 1
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
