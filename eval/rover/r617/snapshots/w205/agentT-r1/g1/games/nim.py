def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = piles[i] ^ x
        if t < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - t)
    return 'LOSE'
