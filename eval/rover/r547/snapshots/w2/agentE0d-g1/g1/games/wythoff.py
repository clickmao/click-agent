def solve(text):
    a, b = map(int, text.split())
    x, y = min(a, b), max(a, b)
    d = y - x
    c = d * (1 + 5 ** 0.5) / 2.0
    l = int(c) + 1
    while l * (1 + 5 ** 0.5) / 2.0 > d or (l + 1) * (1 + 5 ** 0.5) / 2.0 <= d:
        if l * (1 + 5 ** 0.5) / 2.0 > d:
            l -= 1
        else:
            l += 1
    if x == l:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            mm, nn = min(na, nb), max(na, nb)
            dd = nn - mm
            ll = int(dd * (1 + 5 ** 0.5) / 2.0 + 0.5)
            if mm == ll:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
