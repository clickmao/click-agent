"""Multi-pile Nim: find the winning first move (smallest pile index, then its removing count).

Input text layout (the whole stdin):
    line 1: m        (1<=m<=4 piles)
    line 2: a1..am   (1<=ai<=15 stones per pile)

Play: two players alternate, each turn removes any positive number of stones
from exactly one pile; whoever takes the last stone wins.

Output:
    winning for the first player -> "WIN p r"  (p = smallest pile index 1-based,
                                                r = stones removed from pile p)
    otherwise                    -> "LOSE"
No trailing newline.
"""

__all__ = ["solve"]


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1

    piles = []
    while idx < len(lines) and len(piles) < m:
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    # Make the total xor zero by reducing one pile; among all such moves pick
    # the smallest pile index (pile order is fixed, so the first hit is minimal).
    for i, a in enumerate(piles):
        target = a ^ xor          # required new size, always < a because xor != 0
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
