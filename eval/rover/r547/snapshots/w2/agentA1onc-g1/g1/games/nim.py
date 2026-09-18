"""Nim: report a winning move (smallest pile index) or LOSE.

A position is a loss for the mover iff the xor of the pile sizes is zero.
A winning move takes ``r`` stones from a pile, turning the xor to zero.
"""


def solve(text: str) -> str:
    """Return ``WIN p r`` (smallest pile p, stones r) or ``LOSE``."""
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    xor_all = 0
    for a in piles:
        xor_all ^= a

    if xor_all == 0:
        return "LOSE"

    # Pile index 1-based, smallest first: r = a - (a ^ xor_all) > 0.
    for i, a in enumerate(piles, start=1):
        r = a - (a ^ xor_all)
        if r > 0:
            return "WIN %d %d" % (i, r)
    return "LOSE"
