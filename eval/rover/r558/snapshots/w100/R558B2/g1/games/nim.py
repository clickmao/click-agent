def solve(text):
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = a[p] ^ x
        if target < a[p]:
            return 'WIN %d %d' % (p + 1, a[p] - target)
    return 'LOSE'
