def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    idx += 1

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
