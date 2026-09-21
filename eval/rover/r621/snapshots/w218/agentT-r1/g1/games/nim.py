def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor = 0
    for p in piles:
        xor ^= p

    if xor == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        target = p ^ xor
        if target < p:
            return 'WIN %d %d' % (idx + 1, p - target)
    return 'LOSE'
