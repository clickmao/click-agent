"""Game: Nim (remove any positive number from one pile; last stone wins)."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

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
