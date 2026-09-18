def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a
    flip = (text.split()[0] != str(a))
    golden = (1 + 5 ** 0.5) / 2
    k = b - a
    p = int(((a + 1) / golden) )
    losing = False
    for kk in range(0, 26):
        pk = int(kk * golden)
        if pk > 25:
            break
        if (a, b) == (pk, pk + kk):
            losing = True
            break
    if losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            lo = min(na, nb)
            hi = max(na, nb)
            d = hi - lo
            pk = int(d * golden)
            if (lo, hi) == (pk, pk + d):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    i, j = best
    if flip:
        return 'WIN %d %d' % (j, i)
    return 'WIN %d %d' % (i, j)
