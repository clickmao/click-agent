def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while idx < len(lines) and len(piles) < m:
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ xor
        if target < piles[p]:
            return 'WIN %d %d' % (p + 1, piles[p] - target)
    return 'LOSE'
