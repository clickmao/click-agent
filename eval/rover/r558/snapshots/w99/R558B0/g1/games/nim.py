"""Multi-pile Nim winning move."""


def solve(text: str) -> str:
    parts = text.split()
    m = int(parts[0])
    piles = [int(x) for x in parts[1:1 + m]]
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
