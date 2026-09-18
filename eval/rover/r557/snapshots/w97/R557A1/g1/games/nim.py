"""Multi-pile Nim: smallest pile index winning move."""


def _parse(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    return m, piles


def solve(text):
    m, piles = _parse(text)
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
