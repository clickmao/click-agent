"""Nim: report the smallest-index heap and the amount to remove."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx, a - target)
    return 'LOSE'
