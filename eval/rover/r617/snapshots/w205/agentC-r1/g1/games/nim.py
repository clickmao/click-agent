"""Nim: find the smallest-index pile with a winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'

    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            take = p - target
            return 'WIN %d %d' % (idx + 1, take)
    return 'LOSE'
