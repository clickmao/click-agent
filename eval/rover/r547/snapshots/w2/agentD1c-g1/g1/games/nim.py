def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].strip())
    piles = [int(x) for x in lines[1].split()]
    while len(piles) < m:
        piles.append(0)
    x = 0
    for p in piles[:m]:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
