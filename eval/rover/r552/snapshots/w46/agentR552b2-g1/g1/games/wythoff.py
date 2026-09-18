def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()
    a, b = (int(x) for x in lines[0].split())
    losing = set()
    for x in range(0, 30):
        y = x + (1 + 5 ** 0.5) / 2.0
        yi = int(y)
        for dy in (-1, 0, 1):
            yy = yi + dy
            if yy >= 0:
                losing.add((x, yy))
                losing.add((yy, x))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i == 0 or j == 0 or i == j:
                na, nb = a - i, b - j
                if (na, nb) in losing:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
