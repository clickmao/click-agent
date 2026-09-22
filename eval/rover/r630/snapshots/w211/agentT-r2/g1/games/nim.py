"""Nim: m heaps, remove any positive number from one heap, last stone wins."""


def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
