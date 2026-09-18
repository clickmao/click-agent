def solve(text):
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    # losing positions: (floor(k*phi), floor(k*phi^2))
    k = 0
    losing = set()
    while True:
        x = int(k * (1 + 5 ** 0.5) / 2)
        y = x + k
        if x > 25 or y > 25:
            break
        losing.add((x, y))
        k += 1
    orig_a, orig_b = map(int, text.split())
    if (a, b) in losing:
        return 'LOSE'
    best = None
    # remove from one pile only: (i,0) or (0,j)
    for i in range(orig_a + 1):
        for j in range(orig_b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = orig_a - i, orig_b - j
            if na < 0 or nb < 0:
                continue
            x, y = (na, nb) if na <= nb else (nb, na)
            if (x, y) in losing:
                key = (i, j)
                if best is None or key < best:
                    best = key
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
