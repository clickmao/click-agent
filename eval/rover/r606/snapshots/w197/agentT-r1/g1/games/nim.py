"""Nim game: find smallest-index pile with a winning move."""


def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = x ^ piles[idx]
        if target < piles[idx]:
            r = piles[idx] - target
            return 'WIN %d %d' % (idx + 1, r)
    return 'LOSE'
