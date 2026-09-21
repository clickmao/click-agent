"""Nim: take any positive number of stones from a single pile."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(v) for v in data[1:1 + m]]

    xor = 0
    for p in piles:
        xor ^= p

    if xor == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        target = p ^ xor
        if target < p:
            return 'WIN %d %d' % (idx + 1, p - target)
    return 'LOSE'
