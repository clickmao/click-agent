"""Nim: multiple heaps, remove any positive number from one heap.

stdin format:
    m
    a1 ... am
Output: 'WIN p r' (p minimal heap index, r stones taken) or 'LOSE'.
"""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    heaps = [int(x) for x in parts[1:1 + m]]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return "LOSE"
    for idx, a in enumerate(heaps):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
