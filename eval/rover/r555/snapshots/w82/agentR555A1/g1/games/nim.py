def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = [int(x) for x in lines[idx].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        if piles[i] ^ x < piles[i]:
            r = piles[i] - (piles[i] ^ x)
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'
