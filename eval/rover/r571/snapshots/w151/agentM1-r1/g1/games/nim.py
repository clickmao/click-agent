def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].strip())
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            r = piles[i] - target
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'
