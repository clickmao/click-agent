"""Multi-pile Nim: report a winning move (smallest pile index) or LOSE."""


def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    xor = 0
    for v in piles:
        xor ^= v
    if xor == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
