"""Nim (multi-pile, take any positive number from one pile)."""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    a = [int(x) for x in parts[1:1 + m]]

    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return "LOSE"

    for p in range(m):
        target = a[p] ^ x
        take = a[p] - target
        if 1 <= take <= a[p]:
            return "WIN %d %d" % (p + 1, take)
    return "LOSE"
