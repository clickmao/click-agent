"""Multi-pile Nim: find the lexicographically smallest winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
