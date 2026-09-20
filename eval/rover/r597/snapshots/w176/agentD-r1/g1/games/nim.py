def solve(text):
    tokens = text.split()
    if not tokens:
        return ''
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        cur = piles[p - 1]
        target = cur ^ x
        if target < cur:
            return 'WIN %d %d' % (p, cur - target)
    return 'LOSE'
