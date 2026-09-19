def solve(text):
    lines = text.split('\n')
    m = int(lines[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        target = piles[p - 1] ^ x
        if target < piles[p - 1]:
            return 'WIN ' + str(p) + ' ' + str(piles[p - 1] - target)
    return 'LOSE'
