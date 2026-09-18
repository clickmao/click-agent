def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split() if x != '']
    piles = piles[:m]
    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            take = piles[idx] - target
            return 'WIN ' + str(idx + 1) + ' ' + str(take)
    return 'LOSE'
