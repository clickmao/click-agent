def solve(text):
    toks = text.split()
    m = int(toks[0])
    a = [int(x) for x in toks[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        v = a[p - 1]
        t = v ^ x
        if t < v:
            return 'WIN %d %d' % (p, v - t)
    return 'LOSE'
