def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        t = x ^ a
        if t < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - t)
    return 'LOSE'
