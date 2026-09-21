def solve(text):
    lines = text.strip('\n').split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = piles[i] ^ x
        if t < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - t)
    return 'LOSE'
