"""Multi-pile Nim: smallest pile index with a winning reduction."""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    total = 0
    for p in piles:
        total ^= p
    if total == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ total
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
