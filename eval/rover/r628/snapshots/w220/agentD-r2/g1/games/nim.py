"""Multi-pile Nim: WIN p r (smallest pile index, stones removed) or LOSE."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    while lines and lines[-1].strip() == '':
        lines.pop()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
