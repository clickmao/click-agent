def solve(text: str) -> str:
    data = text.split()
    idx = 0
    m = int(data[idx]); idx += 1
    piles = [int(data[idx + i]) for i in range(m)]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
