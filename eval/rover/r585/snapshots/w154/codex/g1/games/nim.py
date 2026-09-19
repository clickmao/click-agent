"""Standard Nim: remove any positive number of stones from a single heap."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    heaps = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for a in heaps:
        x ^= a

    if x == 0:
        return "LOSE"

    for i, a in enumerate(heaps):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)

    return "LOSE"
