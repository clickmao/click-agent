def solve(text):
    vals = text.split()
    m = int(vals[0])
    piles = [int(x) for x in vals[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
