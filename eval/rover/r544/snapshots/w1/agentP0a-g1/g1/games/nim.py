def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    piles = []
    for t in lines[idx + 1].split():
        piles.append(int(t))
    piles = piles[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (i + 1, p - target)
    return 'LOSE'
