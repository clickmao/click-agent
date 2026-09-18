def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
