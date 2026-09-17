"""Multi-pile Nim: find smallest-index winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a

    if xor_sum == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        target = a ^ xor_sum
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
