def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        t = piles[p] ^ x
        if t < piles[p]:
            return 'WIN ' + str(p + 1) + ' ' + str(piles[p] - t)
