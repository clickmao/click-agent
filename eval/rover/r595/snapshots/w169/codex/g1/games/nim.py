"""Multi-pile Nim: smallest-index winning move."""
from functools import reduce


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = reduce(lambda a, b: a ^ b, piles, 0)
    if xor == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
