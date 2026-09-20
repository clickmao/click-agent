"""Multi-pile Nim: find the smallest-index pile winning move."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
