"""Multi-pile Nim (normal play): last player to take a stone wins.

Input (complete stdin text)::

    m
    a1 a2 ... am

On each turn a player removes any positive number of stones from a *single*
pile.  Output: ``WIN p r`` where p is the smallest 1-based pile index among
winning moves and r the number of stones taken from it (unique per pile), or
``LOSE`` when the first player loses.
"""


def solve(text: str) -> str:
    """Return the winning move with the smallest pile index, else LOSE."""
    data = text.split()
    m = int(data[0])
    piles = [int(t) for t in data[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    # Winning move: make a pile equal to (that pile ^ total xor).
    for idx, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:  # leaves a non-zero (winning) position
            return "WIN {} {}".format(idx, a - target)
    return "LOSE"  # unreachable when x != 0
