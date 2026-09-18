def solve(text):
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    d = b - a
    lo, hi = 0, 30
    while lo < hi:
        mid = (lo + hi) // 2
        if mid * (mid + 1) // 2 < d:
            lo = mid + 1
        else:
            hi = mid
    t = lo
    p = t * (3 - t) // 2
    q = p + d
    if a == p and b == q:
        return 'LOSE'
    for i in range(0, b + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            x, y = na, nb
            if x > y:
                x, y = y, x
            dd = y - x
            lo2, hi2 = 0, 30
            while lo2 < hi2:
                mid = (lo2 + hi2) // 2
                if mid * (mid + 1) // 2 < dd:
                    lo2 = mid + 1
                else:
                    hi2 = mid
            t2 = lo2
            pp = t2 * (3 - t2) // 2
            qq = pp + dd
            if x == pp and y == qq:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
