def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    m = int(tokens[pos]); pos += 1
    piles = [int(tokens[pos + i]) for i in range(m)]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return 'WIN %d %d' % (i + 1, v - target)
    return 'LOSE'
