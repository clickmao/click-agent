def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        take = a - (a ^ x)
        if 1 <= take <= a:
            return 'WIN %d %d' % (i + 1, take)
    return 'LOSE'
