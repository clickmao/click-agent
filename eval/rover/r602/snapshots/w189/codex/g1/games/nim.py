"""Nim: find the smallest-index heap with a winning move and its amount."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for p in piles:
        xor ^= p

    if xor == 0:
        return "LOSE"

    for idx, p in enumerate(piles):
        target = p ^ xor
        if target < p:
            return "WIN %d %d" % (idx + 1, p - target)
    return "LOSE"
