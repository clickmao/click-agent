"""Nim: xor criterion, smallest heap index, unique winning removal."""


def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()]
    heaps = heaps[:m]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            r = heaps[idx] - target
            return 'WIN %d %d' % (idx + 1, r)
    return 'LOSE'
