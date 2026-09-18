def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    if not lines:
        return ''
    m = int(lines[0].split()[0])
    piles = []
    if 1 < len(lines):
        piles = list(map(int, lines[1].split()))
    piles = piles[:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
