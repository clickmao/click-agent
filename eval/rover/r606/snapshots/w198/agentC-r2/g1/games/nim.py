"""Multi-pile Nim: smallest-index winning move or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        piles.extend(int(tok) for tok in lines[idx].split())
        idx += 1
    piles = piles[:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            take = a - target
            return 'WIN ' + str(i + 1) + ' ' + str(take)
    return 'LOSE'
