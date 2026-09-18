def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    best = None
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            r = piles[idx] - t
            cand = (idx + 1, r)
            if best is None or cand[0] < best[0]:
                best = cand
    return 'WIN %d %d' % best
