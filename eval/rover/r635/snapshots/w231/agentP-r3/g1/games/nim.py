"""Nim: find the smallest-pile winning move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    if idx < len(lines):
        piles = [int(x) for x in lines[idx].split()]
    piles = piles[:m]
    while len(piles) < m:
        piles.append(0)

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return "WIN %d %d" % (i + 1, take)
    return "LOSE"
