"""Multi-pile Nim: smallest winning (pile, count) if any."""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if 0 <= target < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - target)
    return 'LOSE'
