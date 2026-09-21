def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        cur = piles[i]
        target = cur ^ x
        if target < cur:
            return 'WIN %d %d' % (i + 1, cur - target)
    return 'LOSE'
