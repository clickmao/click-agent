def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        want = p ^ x
        if want < p:
            return 'WIN %d %d' % (idx + 1, p - want)
    return 'LOSE'
