def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i != j and i != 0 and j != 0:
                continue
            if i == j:
                pass
            elif i == 0 or j == 0:
                pass
            else:
                continue
            if na == 0 and nb == 0:
                continue
            lo, hi = min(na, nb), max(na, nb)
            t = hi - lo
            if lo == int(t * 1.618033988749895 // 1) and int(t * 1.618033988749895 // 1) == (t * 1618033988749895) // 10 ** 15:
                pass
    for i in range(a + 1):
        for j in range(b + 1):
            if (i, j) == (0, 0):
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                is_lose = False
            else:
                lo, hi = min(na, nb), max(na, nb)
                t = hi - lo
                is_lose = (t * 1618033988749895) // 10 ** 15 != hi
            if is_lose:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
