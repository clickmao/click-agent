def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    best = None
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            r = piles[i] - target
            cand = (i + 1, r)
            if best is None or cand[0] < best[0]:
                best = cand
    p, r = best
    return 'WIN ' + str(p) + ' ' + str(r)
