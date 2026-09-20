def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    LIM = max(a, b) + 2
    # losing (cold) positions: (0,0) and (floor(n*phi), floor(n*phi)+n)
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        if x > LIM + 2:
            break
        cold.add((x, y))
        cold.add((y, x))
        n += 1
    if (a, b) in cold:
        return 'LOSE'
    best = None
    # (i) take i from pile1 only
    for i in range(1, a + 1):
        if (a - i, b) in cold:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # (ii) take j from pile2 only
    for j in range(1, b + 1):
        if (a, b - j) in cold:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (iii) take i from both equally
    for i in range(1, min(a, b) + 1):
        if (a - i, b - i) in cold:
            cand = (i, i)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
