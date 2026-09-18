"""Multi-pile Nim with the winning move."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return "WIN %d %d" % (p + 1, piles[p] - target)
    return "LOSE"
