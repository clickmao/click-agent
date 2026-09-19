"""Nim: m then m pile sizes. WIN p r (smallest pile, stones to remove) or LOSE."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            r = piles[idx] - target
            return 'WIN %d %d' % (idx + 1, r)
    return 'LOSE'
