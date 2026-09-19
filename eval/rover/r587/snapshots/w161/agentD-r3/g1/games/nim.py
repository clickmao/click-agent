def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        target = piles[p - 1] ^ xor
        if target < piles[p - 1]:
            return 'WIN %d %d' % (p, piles[p - 1] - target)
    return 'LOSE'
