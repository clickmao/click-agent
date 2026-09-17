"""Nim: take any positive number from one pile; last stone wins.

solve(text) -> str : returns "WIN p r" (smallest pile index, stones removed)
or "LOSE".
"""


def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(x) for x in toks[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
