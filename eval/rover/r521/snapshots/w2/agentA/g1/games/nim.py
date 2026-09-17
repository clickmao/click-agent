"""Multi-pile Nim: find the winning move.

stdin:
    line 1: m          (1<=m<=4 piles)
    line 2: m integers a1..am (1<=ai<=15)

Move: remove any positive number of stones from exactly one pile.
Player taking the last stone wins.

stdout:
    "WIN p r" (p = smallest 1-based pile index with a winning move,
               r = stones removed from that pile), or
    "LOSE"
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    assert len(piles) == m

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x          # desired new size of this pile
        if target < a:          # r = a - target > 0, and each pile has <=1 move
            return "WIN %d %d" % (idx + 1, a - target)
    raise AssertionError("unreachable: non-zero xor without winning move")
