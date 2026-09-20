"""Multi-pile Nim: smallest winning pile and the amount to remove from it."""


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
