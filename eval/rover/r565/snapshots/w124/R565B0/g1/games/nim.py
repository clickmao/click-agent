"""Multi-pile Nim: smallest-index pile and amount of a winning first move.

Input format:
    line 1: m   (1<=m<=4 piles)
    line 2: m integers a1..am (1<=ai<=15)

A move removes any positive number of stones from a single pile;
taking the last stone wins.
Output: `WIN p r` (p = 1-based index of the smallest pile having a winning
        move, r = stones removed; at most one winning move per pile),
        or `LOSE` if the first player loses.
"""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
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
