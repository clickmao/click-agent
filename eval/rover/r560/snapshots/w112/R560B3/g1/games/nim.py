def solve(text):
    lines = [ln.strip() for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0])
    if m == 0:
        return 'LOSE'
    piles = list(map(int, lines[1].split()))
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
