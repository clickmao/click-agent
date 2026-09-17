def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return 'LOSE'
    for idx, p in enumerate(piles, 1):
        target = p ^ xor
        if target < p:
            return 'WIN %d %d' % (idx, p - target)
    return 'LOSE'
