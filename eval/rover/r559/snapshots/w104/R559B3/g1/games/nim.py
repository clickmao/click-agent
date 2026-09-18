def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]

    x = 0
    for p in piles:
        x ^= p

    if x == 0:
        return 'LOSE'

    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN ' + str(idx + 1) + ' ' + str(p - target)

    return 'LOSE'
