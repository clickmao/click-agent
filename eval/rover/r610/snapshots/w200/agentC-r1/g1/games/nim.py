"""Multi-pile Nim: WIN p r (smallest pile index) or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    it = iter(lines)
    m = int(next(it).split()[0])
    piles = [int(t) for t in next(it).split()][:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        want = a ^ xor
        if want < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - want)
    return 'LOSE'
