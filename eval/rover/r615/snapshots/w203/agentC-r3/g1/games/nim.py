"""Nim: two players alternately remove any positive number of stones
from a single pile; the player taking the last stone wins.

solve(text) parses:
  line 1: m  (number of piles)
  line 2: a1 .. am (pile sizes)
Returns, when the first player wins, 'WIN p r' where p is the smallest
pile index (1-based) admitting a winning move and r is the number of
stones taken from that pile; otherwise 'LOSE'. No trailing newline.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
