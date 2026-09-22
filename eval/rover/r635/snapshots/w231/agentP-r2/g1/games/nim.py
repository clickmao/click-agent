"""Multi-pile Nim (normal play): smallest heap index with a winning removal, or LOSE.

Input text:
    line 1: m
    line 2: a1 .. am
Output text: 'WIN p r' or 'LOSE'.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or not lines[0].split():
        return 'LOSE'
    m = int(lines[0].split()[0])
    second = lines[1].split() if len(lines) > 1 else []
    piles = [int(x) for x in second[:m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        r = piles[idx] - (x ^ piles[idx])
        if r > 0:
            return 'WIN %d %d' % (idx + 1, r)
    return 'LOSE'
