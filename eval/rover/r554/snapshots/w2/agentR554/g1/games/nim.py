def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        t = a ^ x
        if t < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - t)
    return 'LOSE'
