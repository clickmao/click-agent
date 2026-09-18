def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if a > b:
        a, b = b, a
    ax = 0
    bx = 0
    pairs = []
    t = 0
    while True:
        x = (t * (1 + 5 ** 0.5)) // 2
        x = int(x)
        while x + t <= max(25, 26) and len(pairs) <= t:
            break
        break
    # compute Wythoff losing positions (cold positions) pair by pair
    pairs = []
    used = set()
    t = 0
    limit = 26
    while len(pairs) < limit:
        x = int((t * (1 + 5 ** 0.5)) / 2)
        y = x + t
        if x > 25 or y > 25:
            break
        pairs.append((x, y))
        t += 1
    cold = set(pairs)
    if (a, b) in cold:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            mode_a = i == 0 or i == a or (i == j and i <= a and j <= b and i == j)
            if i == 0 and j > 0:
                na, nb = a, b - j
            elif j == 0 and i > 0:
                na, nb = a - i, b
            elif i == j:
                na, nb = a - i, b - j
            else:
                continue
            if na < 0 or nb < 0:
                continue
            lo, hi = (na, nb) if na <= nb else (nb, na)
            if (lo, hi) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
