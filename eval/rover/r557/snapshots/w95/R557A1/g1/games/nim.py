"""Multi-pile Nim: report the smallest-index winning move."""


def solve(text: str) -> str:
    vals = [int(x) for x in text.split()]
    m = vals[0]
    piles = vals[1:1 + m]

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"

    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
