def solve(text):
    vals = text.split()
    m = int(vals[0])
    piles = [int(x) for x in vals[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
