"""Multi-pile Nim: find the winning move from the lowest-numbered pile."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor_sum = 0
    for value in piles:
        xor_sum ^= value

    if xor_sum == 0:
        return 'LOSE'

    for index, value in enumerate(piles):
        target = value ^ xor_sum
        if target < value:
            return 'WIN {} {}'.format(index + 1, value - target)
    return 'LOSE'
