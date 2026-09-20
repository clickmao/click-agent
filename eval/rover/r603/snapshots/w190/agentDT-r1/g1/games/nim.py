def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'

    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            r = piles[idx] - target
            return 'WIN ' + str(idx + 1) + ' ' + str(r)
    return 'LOSE'
