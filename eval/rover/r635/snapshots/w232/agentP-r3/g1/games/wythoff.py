def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return 'LOSE'
    a, b = map(int, lines[0].split())
    # losing positions: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        losing.add((y, x))
        n += 1
        if n > 100:
            break
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            # single pile removal
            if j == 0 or i == 0:
                if (na, nb) in losing:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
            # both piles equal amount
            if i == j and i > 0:
                if (na, nb) in losing:
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
