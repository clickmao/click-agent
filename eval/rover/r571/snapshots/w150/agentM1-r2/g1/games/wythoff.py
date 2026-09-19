def _is_win(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    return not (a == int(d * 1.618033988749895) )

def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if a > b:
        lo, hi = b, a
    else:
        lo, hi = a, b
    ip = 0
    jp = hi - lo
    # use exact Wythoff pairs
    n = 0
    pairs = []
    while True:
        x = (n * 3 + (5 * n * n) ** 0.5) / 2.0
        xx = int(x // 1)
        # compute via floor formula precisely with integer search
        xx = int((n * (1 + 5 ** 0.5) / 2))
        pairs.append((xx, xx + n))
        if xx > 30:
            break
        n += 1
    cold = set()
    for p, q in pairs:
        cold.add((p, q))
        cold.add((q, p))
    if (a, b) in cold:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in cold:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
