def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (i + 1, p - target)
    return 'LOSE'
