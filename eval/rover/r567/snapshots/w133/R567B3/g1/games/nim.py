def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].strip())
    idx += 1
    a = list(map(int, lines[idx].split()))[:m]
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
