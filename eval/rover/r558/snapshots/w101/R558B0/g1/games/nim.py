"""Multi-pile Nim: smallest-index winning move.

Input text format:
  line 1: m (number of piles)
  line 2: m integers a1..am (stones per pile)
Output:
  'WIN p r' where p is the 1-based index of the smallest-indexed pile
  with a winning move and r stones are removed from it (unique per pile);
  or 'LOSE'.
Last stone taken wins.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
