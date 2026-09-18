def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    while lines[idx].strip() == '':
        idx += 1
    piles = list(map(int, lines[idx].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
