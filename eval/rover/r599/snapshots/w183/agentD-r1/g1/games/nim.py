"""Nim: WIN p r (smallest pile with a winning move) or LOSE."""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    nim_sum = 0
    for a in piles:
        nim_sum ^= a
    if nim_sum == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ nim_sum
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
