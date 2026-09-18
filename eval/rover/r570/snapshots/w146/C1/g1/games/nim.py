def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        r = p - (p ^ x)
        if r > 0:
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'
