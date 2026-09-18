def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ xor
        if target < piles[i]:
            take = piles[i] - target
            return 'WIN %d %d' % (i + 1, take)
    return 'LOSE'
