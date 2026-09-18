"""Nim: take any positive number from one heap, last stone wins."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0])
    heaps = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in heaps:
        x ^= a

    if x == 0:
        return "LOSE"
    for i, a in enumerate(heaps, 1):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i, a - target)
    return "LOSE"
