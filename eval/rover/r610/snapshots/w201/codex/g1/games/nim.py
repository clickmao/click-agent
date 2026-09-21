"""Multi-pile Nim."""
from functools import reduce


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    x = reduce(lambda a, b: a ^ b, piles, 0)
    if x == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
