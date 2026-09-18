def solve(text):
    data = text.split()
    m = int(data[0])
    piles = [int(data[1 + i]) for i in range(m)]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return 'WIN %d %d' % (p + 1, piles[p] - target)
    return 'LOSE'
