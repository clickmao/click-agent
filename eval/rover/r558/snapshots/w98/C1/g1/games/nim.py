def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = [int(x) for x in lines[idx].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (i + 1, p - target)
    return 'LOSE'
