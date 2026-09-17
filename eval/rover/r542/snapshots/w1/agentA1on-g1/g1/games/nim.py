"""Multi-pile Nim: remove any positive number of stones from exactly one pile.

stdin:  first line "m" (number of piles); second line m integers a1..am.
stdout: "WIN p r" (p = smallest 1-based pile index of a winning move,
        r = stones removed from it) if the first player wins, else "LOSE".

Normal play: whoever takes the last stone wins.
A position is losing iff the XOR of all pile sizes is 0.
"""


def solve(text: str) -> str:
    """Pure function: full stdin text -> full stdout text (no trailing newline)."""
    lines = text.splitlines()
    if not lines:
        return ""
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles, start=1):  # smallest pile index first
        target = a ^ x
        if target < a:  # removing a - target leaves XOR 0 == losing for opponent
            return "WIN %d %d" % (idx, a - target)
    return "LOSE"  # unreachable for consistent input
