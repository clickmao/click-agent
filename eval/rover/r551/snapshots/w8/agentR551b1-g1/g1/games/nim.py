"""Nim: smallest-index pile and the amount to take from it."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(tokens[1 + i]) for i in range(m)]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return 'LOSE'

    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - target)
    return 'LOSE'
