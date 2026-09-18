def solve(text: str) -> str:
    vals = text.split()
    m = int(vals[0])
    a = [int(x) for x in vals[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = a[i] ^ x
        if t < a[i]:
            return 'WIN %d %d' % (i + 1, a[i] - t)
    return 'LOSE'
