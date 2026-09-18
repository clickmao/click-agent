def solve(text):
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        a = piles[p - 1]
        t = a ^ x
        if t < a:
            return 'WIN ' + str(p) + ' ' + str(a - t)
    return 'LOSE'
