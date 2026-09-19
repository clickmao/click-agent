def solve(text):
    parts = text.split()
    m = int(parts[0])
    piles = list(map(int, parts[1:1 + m]))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            r = piles[p] - target
            return 'WIN %d %d' % (p + 1, r)
    return 'LOSE'
