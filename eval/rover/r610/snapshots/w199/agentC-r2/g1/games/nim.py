"""Multi-pile Nim: minimal-index winning move."""


def solve(text: str) -> str:
    toks = text.split()
    pos = 0
    m = int(toks[pos]); pos += 1
    piles = []
    for _ in range(m):
        piles.append(int(toks[pos])); pos += 1

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
