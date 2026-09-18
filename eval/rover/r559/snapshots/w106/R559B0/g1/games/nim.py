import sys


def solve(text: str) -> str:
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    m = int(lines[i].split()[0])
    i += 1
    piles = list(map(int, lines[i].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = piles[p] ^ x
        if target < piles[p]:
            return 'WIN ' + str(p + 1) + ' ' + str(piles[p] - target)
    return 'LOSE'
