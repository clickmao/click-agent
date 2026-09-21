def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        r = a[i] - (a[i] ^ x)
        if 0 < r <= a[i]:
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'
