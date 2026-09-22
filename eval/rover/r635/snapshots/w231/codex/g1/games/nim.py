"""Multi-pile Nim: find a winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for p in piles:
        xor ^= p

    if xor == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            take = piles[idx] - target
            return "WIN %d %d" % (idx + 1, take)
    return "LOSE"
