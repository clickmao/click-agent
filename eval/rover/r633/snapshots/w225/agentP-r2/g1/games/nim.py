"""Nim: find the winning move (smallest heap index, stones to remove)."""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    piles = [int(parts[1 + i]) for i in range(m)]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return 'WIN %d %d' % (p + 1, piles[p] - target)
    return 'LOSE'
