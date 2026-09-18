"""Nim game."""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
