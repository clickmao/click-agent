"""Multi-pile Nim (up to 4 piles, each <= 15): find minimal-pile winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ xor
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
