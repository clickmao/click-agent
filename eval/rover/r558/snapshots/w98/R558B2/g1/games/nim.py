def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return 'WIN ' + str(p + 1) + ' ' + str(piles[p] - target)
    return 'LOSE'
