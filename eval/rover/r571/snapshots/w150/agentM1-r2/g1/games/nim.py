def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        cur = piles[idx]
        target = cur ^ x
        if target < cur:
            return 'WIN %d %d' % (idx + 1, cur - target)
    return 'LOSE'
