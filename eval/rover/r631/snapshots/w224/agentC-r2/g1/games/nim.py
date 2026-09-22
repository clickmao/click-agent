def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            take = piles[idx] - target
            return 'WIN ' + str(idx + 1) + ' ' + str(take)
    return 'LOSE'
