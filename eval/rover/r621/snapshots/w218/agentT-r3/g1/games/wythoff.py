def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    m = max(a, b) + 2
    losing = set()
    found = 0
    d = 0
    while found < m:
        j = (d * (1 + 5 ** 0.5)) / 2.0
        i0 = int(j) + 1
        while i0 * i0 - i0 * d - d * d < 0:
            i0 += 1
        while i0 * i0 - i0 * d - d * d > 0:
            i0 -= 1
        i1 = i0 + d
        if i0 > m:
            break
        losing.add((i0, i1))
        losing.add((i1, i0))
        found += 1
        d += 1
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
