def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(x) for x in toks[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        take = a - (a ^ x)
        if 0 < take <= a:
            return 'WIN %d %d' % (i + 1, take)
    return 'LOSE'
