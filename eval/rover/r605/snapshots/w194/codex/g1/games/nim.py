def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
