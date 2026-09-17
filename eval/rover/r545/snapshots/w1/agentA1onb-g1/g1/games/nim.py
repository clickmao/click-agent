"""Multi-pile Nim: find the lexicographically smallest winning move.

stdin:
    first line: m (number of piles)
    second line: m pile sizes
stdout: 'WIN p r' (pile index 1-based, stones removed) or 'LOSE'.
Pure function: solve(text) -> str (no trailing newline).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    # Smallest pile index that can be reduced to make the xor vanish.
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
