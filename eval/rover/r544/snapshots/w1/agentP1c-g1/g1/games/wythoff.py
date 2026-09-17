def solve(text):
    a, b = (int(x) for x in text.split())
    if a > b:
        a, b = b, a

    cold = set()
    i, j = 0, 0
    pairs = []
    while i <= 25 and j <= 25:
        pairs.append((i, j))
        cold.add((i, j))
        i, j = j + 1, i + j + 2

    def is_cold(pa, pb):
        x, y = (pa, pb) if pa <= pb else (pb, pa)
        return (x, y) in cold

    def is_win(di, dj):
        return not is_cold(a - di, b - dj)

    best = None
    for di in range(0, a + 1):
        dj = di
        if b - dj >= 0 and is_win(di, dj):
            cand = (di, dj)
            if best is None or cand < best:
                best = cand
    for di in range(0, a + 1):
        if a - di == 0:
            continue
        if is_win(di, 0):
            cand = (di, 0)
            if best is None or cand < best:
                best = cand
    for dj in range(0, b + 1):
        if b - dj == 0:
            continue
        if is_win(0, dj):
            cand = (0, dj)
            if best is None or cand < best:
                best = cand

    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
