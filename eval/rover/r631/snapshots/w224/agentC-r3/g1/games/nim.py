def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    a = [int(x) for x in toks[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        t = x ^ a[p]
        if t < a[p]:
            r = a[p] - t
            return 'WIN ' + str(p + 1) + ' ' + str(r)
    return 'LOSE'
