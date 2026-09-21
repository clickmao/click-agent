"""Nim game: smallest-index heap first player winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return 'LOSE'
    for p in range(m):
        target = total ^ piles[p]
        if target < piles[p]:
            return 'WIN ' + str(p + 1) + ' ' + str(piles[p] - target)
    return 'LOSE'
