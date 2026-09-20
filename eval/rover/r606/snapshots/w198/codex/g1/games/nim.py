"""Multi-pile Nim: report a winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
