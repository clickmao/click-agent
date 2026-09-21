"""Multi-pile Nim: find the winning move on the lowest-numbered pile."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor_sum = 0
    for size in piles:
        xor_sum ^= size

    if xor_sum == 0:
        return "LOSE"

    for index, size in enumerate(piles):
        target = size ^ xor_sum
        if target < size:
            return "WIN %d %d" % (index + 1, size - target)
    return "LOSE"
