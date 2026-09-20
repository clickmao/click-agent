"""Multi-pile Nim: find the winning move with smallest pile index."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()[:m]]
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
