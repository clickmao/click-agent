"""Multi-pile Nim: smallest-index winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor_all = 0
    for a in piles:
        xor_all ^= a
    if xor_all == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ xor_all
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
