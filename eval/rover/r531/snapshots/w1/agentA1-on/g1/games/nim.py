"""Multi-pile Nim with a constructive first move.

Input (complete stdin text):
    line 1: m       (1..4 piles)
    line 2: a1..am  (1..15 stones per pile)

Rules: remove any positive number of stones from a single pile; last stone wins.

Output:
    'WIN p r' where p is the smallest 1-based pile index admitting a winning
    move taking r stones (each such pile has exactly one r), or 'LOSE'.
"""

from typing import List


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles: List[int] = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        # Need (a - r) ^ (xor ^ a) == 0  =>  a - r == xor ^ a  =>  r == a - (xor ^ a)
        r = a - (xor ^ a)
        if 1 <= r <= a:
            return "WIN {} {}".format(idx + 1, r)
    return "LOSE"
