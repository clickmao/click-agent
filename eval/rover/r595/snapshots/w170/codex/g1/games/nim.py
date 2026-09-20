def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
