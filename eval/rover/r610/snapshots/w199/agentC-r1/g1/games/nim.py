"""Multi-pile Nim, normal play convention.

stdin format:
    line 1: m          (number of piles, 1..4)
    line 2: a1 .. am   (pile sizes)

Output: 'WIN p r' (lowest pile index with a winning move, and amount taken),
        or 'LOSE'. No trailing newline.
"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]

    xor_all = 0
    for a in piles:
        xor_all ^= a

    if xor_all == 0:
        return 'LOSE'

    for i, a in enumerate(piles):
        target = a ^ xor_all          # required new size for this pile
        if target < a:                # legal: take positive amount
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
