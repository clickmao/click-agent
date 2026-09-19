def solve(text):
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        for tok in lines[idx].split():
            piles.append(int(tok))
        idx += 1
    piles = piles[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return 'WIN %d %d' % (p + 1, piles[p] - target)
    return 'LOSE'
