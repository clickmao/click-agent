def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()][:m]
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
