"""Multi-pile Nim: winning move with smallest pile index."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    x = 0
    for p in piles:
        x ^= p

    if x == 0:
        return 'LOSE'

    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (i + 1, p - target)
    return 'LOSE'
