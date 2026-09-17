"""Multi-pile Nim (normal play): first winning move, dropping pile order.
Pure function solve(text) -> str (no trailing newline).
"""


def _parse(text):
    vals = [int(x) for x in text.split()]
    m = vals[0]
    piles = vals[1:1 + m]
    return piles


def solve(text: str) -> str:
    piles = _parse(text)
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    # smallest pile index (1-based) having a winning reduction
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
