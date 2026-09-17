def solve(text):
    toks = text.split()
    if not toks:
        return ''
    m = int(toks[0])
    piles = [int(t) for t in toks[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
