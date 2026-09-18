"""Game ``nim``: normal-play Nim with m (<=4) piles.

stdin:
    line 1:  m                    (1<=m<=4 piles)
    line 2:  a1..am              (1<=ai<=15 stones per pile)
stdout:
    'WIN p r'  winning move: take r stones from pile p (1-based)
    'LOSE'     first player loses
    no trailing newline.

Nim theory: a position is losing iff the XOR of all pile sizes is 0.  When it
is non-zero, a winning move exists in a *unique* pile (the one whose leading
bit matches the XOR), and the required take is also unique for that pile.
Choose the smallest pile index that admits a winning move.
"""

from __future__ import annotations


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for idx, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx, a - target)
    return 'LOSE'
