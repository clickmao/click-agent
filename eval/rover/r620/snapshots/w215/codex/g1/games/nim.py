"""Nim: solve(piles) -> WIN p r / LOSE (p = smallest winning pile, r = take)."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ total
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
