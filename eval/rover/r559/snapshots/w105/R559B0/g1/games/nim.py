"""Nim: smallest-index pile winning move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx in range(m):
        p = piles[idx]
        target = p ^ x
        if target < p:
            r = p - target
            return "WIN %d %d" % (idx + 1, r)
    return "LOSE"
