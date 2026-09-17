"""Multi-pile Nim: report a winning first move (smallest pile index).

stdin format:
    line 1: m            (1<=m<=4 piles)
    line 2: m integers a1..am (1<=ai<=15 stones per pile)
play:
    take any positive number of stones from a single pile; the player
    taking the last stone wins.
stdout:
    "WIN p r"  p = smallest pile index (1-based) having a winning move,
               r = stones removed from that pile (at most one winning move
               per pile), or
    "LOSE"     when the first player loses with optimal play.
"""

__all__ = ["solve"]


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:  # unique winning reduction for this pile
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"  # unreachable
