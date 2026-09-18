"""Multi-pile Nim: smallest-index winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
