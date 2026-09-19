def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        r = piles[i] ^ x
        if r < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - r)
    return 'LOSE'
