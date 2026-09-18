def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(toks[1 + i]) for i in range(m)]

    x = 0
    for v in piles:
        x ^= v

    if x == 0:
        return 'LOSE'

    for idx, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return 'WIN ' + str(idx + 1) + ' ' + str(v - target)
    return 'LOSE'
