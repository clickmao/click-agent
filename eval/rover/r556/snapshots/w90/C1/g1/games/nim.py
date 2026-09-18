"""Multi-pile Nim: report a winning move (pile index and count) or LOSE."""


def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    xor_sum = 0
    for a in piles:
        xor_sum ^= a

    if xor_sum == 0:
        return "LOSE"

    for idx, a in enumerate(piles, start=1):
        target = a ^ xor_sum
        if target < a:
            return "WIN %d %d" % (idx, a - target)

    return "LOSE"
