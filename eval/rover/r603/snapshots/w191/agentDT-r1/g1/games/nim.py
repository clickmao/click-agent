"""Multi-pile Nim: smallest-index winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0])
    piles = list(map(int, lines[1].split()))
    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ total
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
