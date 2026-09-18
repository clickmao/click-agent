"""Multi-pile Nim: minimal winning heap index and removal."""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'

    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
