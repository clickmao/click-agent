"""Nim: smallest-pile-index winning move."""


def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            take = p - target
            return "WIN {} {}".format(idx + 1, take)
    return "LOSE"
