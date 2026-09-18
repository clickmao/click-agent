def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    total = 0
    for p in piles:
        total ^= p

    if total == 0:
        return 'LOSE'

    for i, p in enumerate(piles):
        target = total ^ p
        if target < p:
            return 'WIN %d %d' % (i + 1, p - target)
    return 'LOSE'
