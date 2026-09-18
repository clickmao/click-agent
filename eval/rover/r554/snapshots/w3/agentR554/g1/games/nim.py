def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        r = a[p - 1] - (a[p - 1] ^ x)
        if r > 0:
            return 'WIN %d %d' % (p, r)
    return 'LOSE'
