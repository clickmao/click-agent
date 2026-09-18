def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    m = int(lines[p].split()[0])
    p += 1
    piles = []
    while len(piles) < m and p < len(lines):
        piles.extend(int(t) for t in lines[p].split())
        p += 1
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
