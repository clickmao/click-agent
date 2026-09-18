def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    import math
    def lose(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        xa = d * (1 + math.sqrt(5)) / 2
        return x == int(xa)
    best = None
    if a > 0 and lose(a - 1, b):
        cand = (1, 0)
    else:
        cand = None
    if b > 0 and lose(a, b - 1):
        c2 = (0, 1)
        if cand is None or c2 < cand:
            cand = c2
    dmax = min(a, b)
    for d in range(1, dmax + 1):
        if lose(a - d, b - d):
            c3 = (d, d)
            if cand is None or c3 < cand:
                cand = c3
            break
    if cand is None:
        return 'LOSE'
    return 'WIN %d %d' % cand
