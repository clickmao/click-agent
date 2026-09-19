"""Nim with m heaps: find the smallest-index heap with a winning move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    heaps = [int(t) for t in lines[1].split()]
    assert len(heaps) == m
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"
    for p in range(m):
        target = heaps[p] ^ x
        if target < heaps[p]:
            return "WIN %d %d" % (p + 1, heaps[p] - target)
    return "LOSE"
