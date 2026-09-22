def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = list(map(int, lines[idx].split()))[:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return 'WIN %d %d' % (i + 1, v - target)
    return 'LOSE'
