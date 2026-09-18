"""Nim: remove any positive number from a single pile."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]

    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return 'LOSE'

    target = xor
    for idx, p in enumerate(piles, start=1):
        t = p ^ target
        if t < p:
            return 'WIN %d %d' % (idx, p - t)
    return 'LOSE'
