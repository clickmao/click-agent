def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - t)
    return 'LOSE'
