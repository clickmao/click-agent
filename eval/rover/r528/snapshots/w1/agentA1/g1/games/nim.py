"""Nim: report the smallest-pile winning move or LOSE."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx, a - target)
    return "LOSE"  # unreachable
