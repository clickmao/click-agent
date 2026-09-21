"""Nim game: winning move with smallest pile index."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = 0
    piles = []
    if lines:
        parts = lines[0].split()
        if parts:
            m = int(parts[0])
    if len(lines) > 1:
        piles = [int(x) for x in lines[1].split()]
    piles = piles[:m] if m else piles
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
