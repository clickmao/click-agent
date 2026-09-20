def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        t = p ^ x
        if t < p:
            return 'WIN ' + str(idx + 1) + ' ' + str(p - t)
    return 'LOSE'
