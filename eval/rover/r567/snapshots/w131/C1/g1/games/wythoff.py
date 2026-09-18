def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    lo, hi = min(a, b), max(a, b)
    # cold positions (Beatty sequences) up to 25
    cold = set()
    x, y = 0, 0
    phi = (1 + 5 ** 0.5) / 2
    n = 1
    while x <= 25 and y <= 25:
        x = int(n * phi)
        y = x + n
        cold.add((x, y))
        n += 1
    if (lo, hi) in cold:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            # move (i,j) valid if i==0 or j==0 or i==j
            if not (i == 0 or j == 0 or i == j):
                continue
            nlo, nhi = min(na, nb), max(na, nb)
            if (nlo, nhi) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
