def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ xor
        if target < piles[i]:
            take = piles[i] - target
            return 'WIN ' + str(i + 1) + ' ' + str(take)
    return 'LOSE'
