def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        r = a[p] - (a[p] ^ x)
        if r > 0:
            return 'WIN %d %d' % (p + 1, r)
    return 'LOSE'
