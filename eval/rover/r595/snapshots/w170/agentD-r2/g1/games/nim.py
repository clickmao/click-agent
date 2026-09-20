def solve(text):
    lines = text.splitlines()
    m = int(lines[0].strip())
    piles = [int(x) for x in lines[1].split()]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        t = a ^ x
        if t < a:
            return 'WIN %d %d' % (idx + 1, a - t)
    return 'LOSE'
