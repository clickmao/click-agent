"""Nim game."""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    piles = [int(x) for x in parts[1:1 + m]]
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
