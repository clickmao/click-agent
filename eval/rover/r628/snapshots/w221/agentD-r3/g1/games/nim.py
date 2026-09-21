def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        v = piles[idx]
        target = v ^ x
        if target < v:
            return 'WIN ' + str(idx + 1) + ' ' + str(v - target)
    return 'LOSE'
