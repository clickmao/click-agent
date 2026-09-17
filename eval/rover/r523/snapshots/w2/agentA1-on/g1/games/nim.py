"""Nim: take any positive number from a single heap; report lowest-index winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    heaps = [int(x) for x in tokens[1:1 + m]]

    xor = 0
    for a in heaps:
        xor ^= a
    if xor == 0:
        return 'LOSE'

    for idx, a in enumerate(heaps):
        target = a ^ xor  # desired heap size after the move
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'  # unreachable when xor != 0
