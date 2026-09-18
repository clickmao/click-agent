def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    m = int(tokens[pos]); pos += 1
    piles = []
    for _ in range(m):
        piles.append(int(tokens[pos])); pos += 1
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return 'WIN ' + str(i + 1) + ' ' + str(take)
    return 'LOSE'
