def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))
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
