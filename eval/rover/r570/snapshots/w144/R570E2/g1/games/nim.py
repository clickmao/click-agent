"""Multi-pile Nim: WIN p r (smallest pile index, remove r) or LOSE."""
from functools import reduce


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = reduce(lambda a, b: a ^ b, piles, 0)
    if x == 0:
        return 'LOSE'
    for p in range(m):
        a = piles[p]
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (p + 1, a - target)
    return 'LOSE'
