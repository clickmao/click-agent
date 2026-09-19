def solve(text):
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])
    # 必败点 (cold positions): (floor(k*phi), floor(k*phi*phi)) 及其对称
    fail = set()
    k = 0
    phi = (1 + 5 ** 0.5) / 2.0
    while True:
        x = int(k * phi)
        y = int(k * phi * phi)
        if x > 26 and y > 26:
            break
        fail.add((x, y))
        fail.add((y, x))
        k += 1
        if k > 1000:
            break
    if (a, b) in fail:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in fail:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
