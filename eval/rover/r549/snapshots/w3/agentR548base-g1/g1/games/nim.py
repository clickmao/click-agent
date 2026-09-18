"""Nim: move removes any positive number of stones from a single heap; last stone wins.

Stdin format: first line m (number of heaps), second line m integers.
Output: 'WIN p r' (smallest heap index, then take r from it) or 'LOSE'.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    m = int(lines[i].split()[0])
    i += 1
    heaps = []
    while i < len(lines) and len(heaps) < m:
        heaps.extend(int(x) for x in lines[i].split())
        i += 1
    heaps = heaps[:m]

    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'

    for idx, a in enumerate(heaps, start=1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx, a - target)
    return 'LOSE'
