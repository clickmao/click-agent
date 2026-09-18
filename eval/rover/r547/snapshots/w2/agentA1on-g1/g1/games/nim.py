"""Multi-pile Nim: take any positive amount from one pile, last stone wins."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'

    for idx in range(m):  # smallest pile index (1-based) first
        a = piles[idx]
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
