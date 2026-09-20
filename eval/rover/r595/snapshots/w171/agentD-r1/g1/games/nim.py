def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))
    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ total
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
