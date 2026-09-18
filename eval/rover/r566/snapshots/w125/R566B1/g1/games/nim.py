"""Multi-pile Nim: m then m pile sizes."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if len(lines) >= 1 and lines[-1] == '':
        lines = lines[:-1]
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
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
